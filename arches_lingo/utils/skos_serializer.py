"""Shared SKOS serialization for Lingo schemes and concepts.

This module is the single source of truth for turning Lingo tile data into SKOS
triples. It is used both by the batch thesaurus exporter (whole-hierarchy file
dumps) and by the content-negotiated dereferencing views (a single resource
serialized live in response to an ``Accept`` header).

The triple mapping and per-nodegroup extraction previously lived inline in the
exporter; they were moved here so that a dereferenced concept and the same
concept in a bulk export can never diverge.
"""

import json
import logging
from collections import defaultdict

from django.utils.translation import gettext as _

from pyld import jsonld
from rdflib import Literal
from rdflib.namespace import DCTERMS, OWL, SKOS

from arches.app.models.models import ResourceInstance, TileModel
from arches_querysets.models import ResourceTileTree

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    SCHEMES_GRAPH_ID,
    TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)
from arches_lingo.utils.skos import SKOSWriter, subject_uri_for

logger = logging.getLogger(__name__)


"""
Mapping dict consists of nodegroup aliases as top level keys. Their values are dicts
where the key indicates the component of a triple and the value are node aliases which
are used to extract data from Arches Queryset TileTrees. There is also an option to
define a default predicate if a predicate is not found in the tile tree. Some predicates
are hardcoded SKOS predicates for specific relationships.

nodegroup_alias: {
    "predicate": "<predicate_node_alias>" | "<skos_predicate_value>",
    "object": "<object_node_alias>",
    "object_language": "<object_language_node_alias>" (optional)
    "default_predicate": "<default_predicate_value>" (optional)
}
"""
TILE_TREE_TO_TRIPLE_MAPPING = {
    # Scheme and Concept Mappings:
    "appellative_status": {
        "predicate": "appellative_status_ascribed_relation",
        "object": "appellative_status_ascribed_name_content",
        "object_language": "appellative_status_ascribed_name_language",
    },
    "identifier": {
        "predicate": "identifier_type",
        "object": "identifier_content",
    },
    "statement": {
        "predicate": "statement_type",
        "object": "statement_content",
        "object_language": "statement_language",
    },
    # Concept Mappings:
    "top_concept_of": {
        "predicate": "hasTopConcept",  # hardcoded SKOS predicate
        "object": "top_concept_of",
    },
    "part_of_scheme": {
        "predicate": "inScheme",  # hardcoded SKOS predicate
        "object": "part_of_scheme",
    },
    # Hierarchy
    "classification_status": {
        "predicate": "classification_status_ascribed_relation",
        "object": "classification_status_ascribed_classification",
        "default_predicate": "broader",
    },
    # Associated Concepts
    "relation_status": {
        "predicate": "relation_status_ascribed_relation",
        "object": "relation_status_ascribed_comparate",
        "default_predicate": "related",
    },
    # Mapping/match relationships to concepts in other vocabularies. The comparate
    # holds an external (or locally-resolvable) URI rather than a resource instance,
    # so its object is emitted as a URI reference, not a string literal.
    "match_status": {
        "predicate": "match_status_ascribed_relation",
        "object": "match_status_ascribed_comparate",
        "object_is_uri": True,
        "default_predicate": "mappingRelation",
    },
}


def extract_triples_from_aliased_tiles(nodegroup_alias, tile_trees):
    """Build triple dicts for a single nodegroup's tile(s) using the mapping table."""
    triples = []
    mapping = TILE_TREE_TO_TRIPLE_MAPPING.get(nodegroup_alias)
    if mapping is None:
        logger.error("No mapping found for nodegroup alias: %s", nodegroup_alias)
        return []
    if type(tile_trees) is not list:
        tile_trees = [tile_trees]
    for tile_tree in tile_trees:
        triple = defaultdict(str)
        for triple_component, node_alias in mapping.items():
            if triple_component == "object_is_uri":
                # A flag (not a node lookup) carried through to the writer.
                triple[triple_component] = node_alias
                continue
            if node_alias in ["inScheme", "hasTopConcept"]:
                # Predicate for concept -> scheme relationship is not stored as a node
                # value but instead derived from the relationship itself
                triple[triple_component] = node_alias
            elif (
                triple_component == "default_predicate" and triple["predicate"] is None
            ):
                # Fall back on default predicates for relationships if none was found
                triple["predicate"] = node_alias
            elif triple_component != "default_predicate":
                try:
                    predicate = getattr(tile_tree.aliased_data, node_alias)
                except AttributeError:
                    # Expected when we've directly mapped a relationship that won't be
                    # wrapped as AliasedData as returned from a queryset (e.g.
                    # top_concept_of and part_of_scheme during partial hierarchy export)
                    predicate = tile_tree
                triple[triple_component] = predicate
        triples.append(triple)
    return triples


def build_triples_for_resource(resource):
    """Build the full list of SKOS triple dicts for one scheme or concept resource.

    Only nodegroups that appear in ``TILE_TREE_TO_TRIPLE_MAPPING`` are considered;
    unmapped nodegroups (images, namespace, status, etc.) contribute no triples.
    """
    triples = []
    for nodegroup_alias in TILE_TREE_TO_TRIPLE_MAPPING:
        tile_trees = getattr(resource.aliased_data, nodegroup_alias, None)
        if tile_trees:
            triples.extend(
                extract_triples_from_aliased_tiles(nodegroup_alias, tile_trees)
            )
    return triples


def collect_referenced_resource_ids(triples):
    """Return the set of resourceinstanceids referenced as triple objects.

    These are the other concepts/schemes that a resource points at (broader,
    related, inScheme, hasTopConcept), whose public URIs we also want to resolve
    so that links between resources use canonical URIs rather than UUID URIs.
    """
    referenced_ids = set()
    for triple in triples:
        triple_object = triple.get("object")
        if isinstance(triple_object, ResourceInstance):
            referenced_ids.add(str(triple_object.resourceinstanceid))
    return referenced_ids


def build_scheme_top_concept_triples(scheme_id):
    """Build ``skos:hasTopConcept`` triples for a scheme from its concepts' tiles.

    The top-concept relationship is stored on each concept's ``top_concept_of``
    tile, so it is invisible when a scheme is serialized on its own. We recover it
    by finding every concept that names this scheme as a top concept.
    """
    top_concept_ids = TileModel.objects.filter(
        nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
        **{
            f"data__{TOP_CONCEPT_OF_NODE_AND_NODEGROUP}__contains": [
                {"resourceId": str(scheme_id)}
            ]
        },
    ).values_list("resourceinstance_id", flat=True)

    triples = []
    for top_concept_id in top_concept_ids:
        triple = defaultdict(str)
        triple["predicate"] = "hasTopConcept"
        triple["object"] = ResourceInstance(resourceinstanceid=top_concept_id)
        triples.append(triple)
    return triples


def build_resource_uri_map(resource_ids):
    """Map resourceinstanceid (str) -> stored public URI string.

    Resources without a minted URI tile (e.g. unpublished drafts) are simply
    absent from the map; callers fall back to the UUID-based ARCHES URI.
    """
    string_ids = [str(resource_id) for resource_id in resource_ids if resource_id]
    if not string_ids:
        return {}
    uri_tiles = TileModel.objects.filter(
        nodegroup_id=URI_NODEGROUP,
        resourceinstance_id__in=string_ids,
    ).values("resourceinstance_id", "data")
    uri_map = {}
    for uri_tile in uri_tiles:
        uri_value = (uri_tile["data"] or {}).get(URI_CONTENT_NODE)
        if uri_value:
            uri_map[str(uri_tile["resourceinstance_id"])] = uri_value
    return uri_map


def graph_kind_for_graph_id(graph_id):
    """Return "scheme" or "concept" for a Lingo graph id, or None if neither."""
    if str(graph_id) == SCHEMES_GRAPH_ID:
        return "scheme"
    if str(graph_id) == CONCEPTS_GRAPH_ID:
        return "concept"
    return None


def serialize_resource(resource_id, graph_kind, rdf_format, *, mark_deprecated=False):
    """Serialize a single scheme or concept as SKOS in the requested RDF format.

    Returns a ``(body_bytes, content_type)`` tuple, or ``(None, None)`` if the
    resource could not be found or produced no triples.
    """
    format_spec = RDF_FORMATS[rdf_format]
    graph_slug = "scheme" if graph_kind == "scheme" else "concept"

    resource = ResourceTileTree.get_tiles(
        graph_slug=graph_slug, resource_ids=[resource_id]
    ).first()
    if resource is None:
        return None, None

    triples = build_triples_for_resource(resource)
    if graph_kind == "scheme":
        # A scheme's top concepts are recorded on the concept tiles, so when
        # serializing the scheme in isolation we enumerate them here.
        triples.extend(build_scheme_top_concept_triples(resource_id))
    if not triples:
        logger.warning(_("No SKOS triples could be built for resource %s"), resource_id)
        return None, None

    referenced_ids = collect_referenced_resource_ids(triples)
    resource_uri_map = build_resource_uri_map({str(resource_id), *referenced_ids})

    triples_by_resource = {resource.resourceinstanceid: triples}
    writer = SKOSWriter()
    if graph_kind == "scheme":
        rdf_graph = writer.write_skos_from_triples(
            triples_by_resource, {}, resource_uri_map=resource_uri_map
        )
    else:
        rdf_graph = writer.write_skos_from_triples(
            {}, triples_by_resource, resource_uri_map=resource_uri_map
        )

    if mark_deprecated:
        rdf_graph.add(
            (
                subject_uri_for(resource_id, resource_uri_map),
                OWL.deprecated,
                Literal(True),
            )
        )

    if rdf_format == "jsonld":
        body = _serialize_graph_as_jsonld(rdf_graph)
    else:
        body = rdf_graph.serialize(format=format_spec["rdflib"])
        if isinstance(body, str):
            body = body.encode("utf-8")
    return body, format_spec["content_type"]


def _serialize_graph_as_jsonld(rdf_graph):
    """Serialize an rdflib graph to compacted JSON-LD.

    The installed rdflib (4.2.2) has no JSON-LD serializer, so we bridge through
    N-Triples and pyld (already an Arches dependency), then compact against the
    SKOS/DCTERMS/OWL namespaces for a readable document.
    """
    ntriples = rdf_graph.serialize(format="nt")
    if isinstance(ntriples, bytes):
        ntriples = ntriples.decode("utf-8")
    expanded = jsonld.from_rdf(ntriples, {"format": "application/nquads"})
    context = {
        "skos": str(SKOS),
        "dcterms": str(DCTERMS),
        "owl": str(OWL),
    }
    compacted = jsonld.compact(expanded, context)
    return json.dumps(compacted, indent=2, sort_keys=True).encode("utf-8")


# --- Content negotiation -------------------------------------------------------

# Registry of the RDF serializations Lingo exposes for dereferenced resources.
# Keyed by the short format token also accepted as a ?format= query value.
RDF_FORMATS = {
    "jsonld": {
        "rdflib": "json-ld",
        "content_type": "application/ld+json",
        "accept_types": ["application/ld+json"],
    },
    "xml": {
        "rdflib": "pretty-xml",
        "content_type": "application/rdf+xml",
        "accept_types": ["application/rdf+xml"],
    },
    "turtle": {
        "rdflib": "turtle",
        "content_type": "text/turtle; charset=utf-8",
        "accept_types": ["text/turtle"],
    },
    "nt": {
        "rdflib": "nt",
        "content_type": "application/n-triples",
        "accept_types": ["application/n-triples"],
    },
}

# Aliases tolerated in the ?format= query string.
_FORMAT_ALIASES = {
    "json-ld": "jsonld",
    "ttl": "turtle",
    "rdf": "xml",
    "rdfxml": "xml",
    "n-triples": "nt",
    "ntriples": "nt",
}

_HTML_TYPES = {"text/html", "application/xhtml+xml"}

# Sentinel returned when a client explicitly demands a format we do not offer.
NOT_ACCEPTABLE = object()

_ACCEPT_TYPE_TO_FORMAT = {
    accept_type: rdf_format
    for rdf_format, spec in RDF_FORMATS.items()
    for accept_type in spec["accept_types"]
}


def _parse_accept_header(accept_header):
    """Return media types from an Accept header, most-preferred first (by q-value)."""
    media_types = []
    for index, part in enumerate(accept_header.split(",")):
        segments = part.strip().split(";")
        media_type = segments[0].strip().lower()
        if not media_type:
            continue
        quality = 1.0
        for parameter in segments[1:]:
            parameter = parameter.strip()
            if parameter.startswith("q="):
                try:
                    quality = float(parameter[2:])
                except ValueError:
                    quality = 0.0
        # Preserve original order for equal q-values with a stable secondary key.
        media_types.append((media_type, quality, index))
    media_types.sort(key=lambda entry: (-entry[1], entry[2]))
    return [media_type for media_type, _quality, _index in media_types]


def negotiate_rdf_format(accept_header, explicit_format=None):
    """Resolve the desired representation for a dereferenced resource.

    Returns one of:
    - a key in ``RDF_FORMATS`` (serve that RDF representation),
    - ``None`` (serve the HTML single-page app — the default for browsers),
    - ``NOT_ACCEPTABLE`` (client explicitly asked for an unsupported ?format=).
    """
    if explicit_format:
        explicit_format = explicit_format.strip().lower()
        explicit_format = _FORMAT_ALIASES.get(explicit_format, explicit_format)
        if explicit_format == "html":
            return None
        if explicit_format in RDF_FORMATS:
            return explicit_format
        return NOT_ACCEPTABLE

    if not accept_header:
        return None

    for media_type in _parse_accept_header(accept_header):
        if media_type in _HTML_TYPES or media_type == "*/*":
            return None
        if media_type in _ACCEPT_TYPE_TO_FORMAT:
            return _ACCEPT_TYPE_TO_FORMAT[media_type]
    return None
