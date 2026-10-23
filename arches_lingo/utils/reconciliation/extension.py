"""W3C reconciliation data extension, read off each concept's dereferenced SKOS.

Values come from the same tile-to-SKOS mapping the content-negotiated concept
URIs serve, so a column pulled into OpenRefine always agrees with the published
RDF for that concept.
"""

import json
import uuid
from dataclasses import dataclass

from django.conf import settings
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from rdflib import Literal
from rdflib.namespace import DCTERMS, SKOS

from arches.app.models.models import TileModel
from arches_querysets.models import ResourceTileTree

from arches_lingo.const import URI_CONTENT_NODE, URI_NODEGROUP
from arches_lingo.utils.reconciliation.candidates import MAX_QUERIES_PER_REQUEST
from arches_lingo.utils.reconciliation.concept_summaries import (
    get_display_labels_for_concepts,
)
from arches_lingo.utils.reconciliation.labels import is_same_base_language
from arches_lingo.utils.reconciliation.manifest import list_reconcilable_schemes
from arches_lingo.utils.reconciliation.visibility import (
    filter_public_concept_ids,
    reconcilable_scheme_ids,
)
from arches_lingo.utils.skos import ARCHES, SKOSWriter, subject_uri_for
from arches_lingo.utils.skos_serializer import (
    build_resource_uri_map,
    build_triples_for_resource,
    collect_referenced_resource_ids,
)

ALL_LANGUAGES = "*"
MATCH_PROPERTY_IDS = ("exactMatch", "closeMatch")


@dataclass(frozen=True)
class ExtensionProperty:
    name: object
    predicate: object = None
    is_language_filtered: bool = False


# "uri", "broader" and "inScheme" are special-cased: the first is the subject
# itself, broader values are concepts returned as reconciled entities, and a
# scheme is returned by name because it is not an entity in this service's
# identifier space.
EXTENSION_PROPERTIES = {
    "uri": ExtensionProperty(gettext_lazy("URI")),
    "notation": ExtensionProperty(gettext_lazy("Identifier"), DCTERMS.identifier),
    "prefLabel": ExtensionProperty(
        gettext_lazy("Preferred label"), SKOS.prefLabel, is_language_filtered=True
    ),
    "altLabel": ExtensionProperty(
        gettext_lazy("Alternate label"), SKOS.altLabel, is_language_filtered=True
    ),
    "broader": ExtensionProperty(gettext_lazy("Broader concept"), SKOS.broader),
    "inScheme": ExtensionProperty(gettext_lazy("Scheme"), SKOS.inScheme),
    "exactMatch": ExtensionProperty(gettext_lazy("Exact match"), SKOS.exactMatch),
    "closeMatch": ExtensionProperty(gettext_lazy("Close match"), SKOS.closeMatch),
    "scopeNote": ExtensionProperty(
        gettext_lazy("Scope note"), SKOS.scopeNote, is_language_filtered=True
    ),
    "definition": ExtensionProperty(
        gettext_lazy("Definition"), SKOS.definition, is_language_filtered=True
    ),
}


def propose_properties(type_id, raw_limit=None):
    """List the extension properties; every scheme offers the same ones."""
    try:
        limit = int(raw_limit) if raw_limit else len(EXTENSION_PROPERTIES)
    except ValueError:
        raise ValueError(_("The limit must be a positive integer."))
    if limit < 1:
        raise ValueError(_("The limit must be a positive integer."))
    return {
        "type": type_id,
        "properties": [
            {"id": property_id, "name": str(extension_property.name)}
            for property_id, extension_property in EXTENSION_PROPERTIES.items()
        ][:limit],
    }


def parse_extension_request(raw_extension_request):
    """Return ``(concept_ids, [(property_id, language)])``; raise ValueError if malformed."""
    try:
        extension_request = json.loads(raw_extension_request)
    except (TypeError, ValueError):
        raise ValueError(_("The extend parameter must be a JSON object."))
    if not isinstance(extension_request, dict):
        raise ValueError(_("The extend parameter must be a JSON object."))

    concept_ids = extension_request.get("ids")
    if not isinstance(concept_ids, list) or not all(
        isinstance(concept_id, str) for concept_id in concept_ids
    ):
        raise ValueError(_('The extend parameter needs an "ids" list of strings.'))
    if len(concept_ids) > MAX_QUERIES_PER_REQUEST:
        raise ValueError(
            _("At most %(limit)s ids can be extended at once.")
            % {"limit": MAX_QUERIES_PER_REQUEST}
        )

    raw_properties = extension_request.get("properties")
    if not isinstance(raw_properties, list):
        raise ValueError(_('The extend parameter needs a "properties" list.'))
    requested_properties = []
    for raw_property in raw_properties:
        property_id = raw_property.get("id") if isinstance(raw_property, dict) else None
        if property_id not in EXTENSION_PROPERTIES:
            raise ValueError(
                _("Unknown extension property: %(property_id)s")
                % {"property_id": property_id}
            )
        # Rows are keyed by property id, so each may be requested only once.
        if any(
            property_id == requested_property_id
            for requested_property_id, _language in requested_properties
        ):
            raise ValueError(
                _("Extension property requested twice: %(property_id)s")
                % {"property_id": property_id}
            )
        property_settings = raw_property.get("settings") or {}
        if not isinstance(property_settings, dict):
            raise ValueError(_("Extension property settings must be a JSON object."))
        language = property_settings.get("lang") or None
        if language is not None and not isinstance(language, str):
            raise ValueError(_('The "lang" setting must be a string.'))
        requested_properties.append((property_id, language))
    return concept_ids, requested_properties


def canonical_id_by_requested_id(requested_ids):
    canonical_ids = {}
    for requested_id in requested_ids:
        try:
            canonical_ids[requested_id] = str(uuid.UUID(requested_id))
        except ValueError:
            continue
    return canonical_ids


def build_skos_graph(concept_ids):
    """Return ``(rdf_graph, resource_uri_map)`` for these concepts, as dereferenced."""
    triples_by_resource_id = {
        resource.resourceinstanceid: build_triples_for_resource(resource)
        for resource in ResourceTileTree.get_tiles(
            graph_slug="concept", resource_ids=concept_ids
        )
    }
    referenced_ids = set()
    for triples in triples_by_resource_id.values():
        referenced_ids |= collect_referenced_resource_ids(triples)
    resource_uri_map = build_resource_uri_map({*concept_ids, *referenced_ids})
    rdf_graph = SKOSWriter().write_skos_from_triples(
        {}, triples_by_resource_id, resource_uri_map=resource_uri_map
    )
    return rdf_graph, resource_uri_map


def resource_id_for_uri(rdf_object, resource_ids_by_public_uri):
    """Map a SKOS object URI back to a resource id: minted URI or UUID-based URI."""
    uri = str(rdf_object)
    if uri in resource_ids_by_public_uri:
        return resource_ids_by_public_uri[uri]
    # Anything else is not a resource, so it never matches a public resource id.
    return uri.removeprefix(str(ARCHES))


def find_non_public_local_uris(uris, public_scheme_ids):
    """Return the URIs that name a resource in this instance that is not public,
    so a match column never reveals the id of, say, a draft concept. Public
    concepts and reconcilable schemes are both kept."""
    if not uris:
        return set()
    resource_id_by_uri = {}
    for uri in uris:
        if not uri.startswith(str(ARCHES)):
            continue
        try:
            resource_id_by_uri[uri] = str(uuid.UUID(uri.removeprefix(str(ARCHES))))
        except ValueError:
            continue
    minted_uri_tiles = TileModel.objects.filter(
        nodegroup_id=URI_NODEGROUP,
        **{f"data__{URI_CONTENT_NODE}__in": list(uris)},
    ).values_list(f"data__{URI_CONTENT_NODE}", "resourceinstance_id")
    for uri, resource_id in minted_uri_tiles:
        resource_id_by_uri[uri] = str(resource_id)

    local_resource_ids = set(resource_id_by_uri.values())
    public_resource_ids = filter_public_concept_ids(
        local_resource_ids, public_scheme_ids
    ) | (local_resource_ids & public_scheme_ids)
    return {
        uri
        for uri, resource_id in resource_id_by_uri.items()
        if resource_id not in public_resource_ids
    }


def matches_language(rdf_object, language):
    if language == ALL_LANGUAGES or not isinstance(rdf_object, Literal):
        return True
    return not rdf_object.language or is_same_base_language(
        rdf_object.language, language
    )


def collect_property_values(
    rdf_graph,
    resource_uri_map,
    concept_ids,
    requested_properties,
    default_language,
    public_scheme_ids,
):
    """Return ``{concept_id: {property_id: [value, …]}}`` in a fixed number of queries."""
    resource_ids_by_public_uri = {
        uri: resource_id for resource_id, uri in resource_uri_map.items()
    }
    objects_by_request = {
        (concept_id, property_id): sorted(
            rdf_graph.objects(
                subject_uri_for(concept_id, resource_uri_map),
                EXTENSION_PROPERTIES[property_id].predicate,
            ),
            key=str,
        )
        for concept_id in concept_ids
        for property_id, _language in requested_properties
        if EXTENSION_PROPERTIES[property_id].predicate is not None
    }

    linked_resource_ids = {
        resource_id_for_uri(rdf_object, resource_ids_by_public_uri)
        for (_concept_id, property_id), rdf_objects in objects_by_request.items()
        if property_id in ("broader", "inScheme")
        for rdf_object in rdf_objects
    }
    public_linked_concept_ids = filter_public_concept_ids(
        linked_resource_ids, public_scheme_ids
    )
    non_public_local_uris = find_non_public_local_uris(
        {
            str(rdf_object)
            for (_concept_id, property_id), rdf_objects in objects_by_request.items()
            if property_id in MATCH_PROPERTY_IDS
            for rdf_object in rdf_objects
        },
        public_scheme_ids,
    )
    scheme_name_by_id = {
        reconciliation_type["id"]: reconciliation_type["name"]
        for reconciliation_type in list_reconcilable_schemes(linked_resource_ids)
    }

    def name_language_for(language):
        return default_language if language in (None, ALL_LANGUAGES) else language

    concept_names_by_language = {
        name_language: get_display_labels_for_concepts(
            public_linked_concept_ids, name_language
        )
        for name_language in {
            name_language_for(language)
            for property_id, language in requested_properties
            if property_id == "broader"
        }
    }

    values_by_concept_id = {}
    for concept_id in concept_ids:
        values_by_property_id = {}
        for property_id, language in requested_properties:
            extension_property = EXTENSION_PROPERTIES[property_id]
            rdf_objects = objects_by_request.get((concept_id, property_id), [])
            if property_id == "uri":
                public_uri = resource_uri_map.get(concept_id)
                values = [{"str": public_uri}] if public_uri else []
            elif property_id == "broader":
                concept_names = concept_names_by_language[name_language_for(language)]
                linked_ids = [
                    resource_id_for_uri(rdf_object, resource_ids_by_public_uri)
                    for rdf_object in rdf_objects
                ]
                values = [
                    {"id": linked_id, "name": concept_names.get(linked_id) or linked_id}
                    for linked_id in linked_ids
                    if linked_id in public_linked_concept_ids
                ]
            elif property_id == "inScheme":
                linked_ids = [
                    resource_id_for_uri(rdf_object, resource_ids_by_public_uri)
                    for rdf_object in rdf_objects
                ]
                values = [
                    {"str": scheme_name_by_id[linked_id]}
                    for linked_id in linked_ids
                    if linked_id in scheme_name_by_id
                ]
            else:
                values = [
                    {"str": str(rdf_object)}
                    for rdf_object in rdf_objects
                    if str(rdf_object) not in non_public_local_uris
                    and (
                        not extension_property.is_language_filtered
                        or matches_language(rdf_object, language or default_language)
                    )
                ]
            values_by_property_id[property_id] = values
        values_by_concept_id[concept_id] = values_by_property_id
    return values_by_concept_id


def extend_concepts(raw_extension_request, scope_scheme_id=None):
    """Answer a data extension request with ``{"meta": [...], "rows": {...}}``.

    Ids that are unknown or not public get empty rows, never an error, so the
    response cannot reveal whether a draft exists. A scheme's own service
    (``scope_scheme_id``) only extends that scheme's concepts.
    """
    requested_ids, requested_properties = parse_extension_request(raw_extension_request)
    canonical_ids = canonical_id_by_requested_id(requested_ids)
    public_scheme_ids = reconcilable_scheme_ids()
    extendable_scheme_ids = (
        public_scheme_ids
        if scope_scheme_id is None
        else public_scheme_ids & {scope_scheme_id}
    )
    public_ids = filter_public_concept_ids(
        set(canonical_ids.values()), extendable_scheme_ids
    )

    meta = [
        {"id": property_id, "name": str(EXTENSION_PROPERTIES[property_id].name)}
        for property_id, _language in requested_properties
    ]
    rows = {
        requested_id: {
            property_id: [] for property_id, _language in requested_properties
        }
        for requested_id in requested_ids
    }
    if not public_ids:
        return {"meta": meta, "rows": rows}

    rdf_graph, resource_uri_map = build_skos_graph(sorted(public_ids))
    values_by_concept_id = collect_property_values(
        rdf_graph,
        resource_uri_map,
        public_ids,
        requested_properties,
        get_language() or settings.LANGUAGE_CODE,
        public_scheme_ids,
    )
    for requested_id, canonical_id in canonical_ids.items():
        if canonical_id in values_by_concept_id:
            rows[requested_id] = values_by_concept_id[canonical_id]
    return {"meta": meta, "rows": rows}
