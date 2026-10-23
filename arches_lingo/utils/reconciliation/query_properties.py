"""SKOS-named properties a reconciliation query can use to narrow its matches.

Property ids are SKOS local names, matching the manifest's ``schemaSpace``.
"""

from collections import defaultdict
from dataclasses import dataclass
from functools import reduce
from operator import or_

from django.db.models import Q
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from arches.app.models.models import TileModel

from arches_lingo.const import (
    ALT_LABEL_URI,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_TYPE_NODE,
    EXACT_MATCH_LIST_ITEM_ID,
    IDENTIFIER_CONTENT_NODE,
    IDENTIFIER_NODEGROUP,
    MATCH_STATUS_COMPARATE_NODE,
    MATCH_STATUS_NODEGROUP,
    MATCH_STATUS_RELATION_NODE,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)
from arches_lingo.utils.concept_merge.tiles import get_list_item_tile_value
from arches_lingo.utils.reconciliation.concept_summaries import (
    get_public_broader_ids_for_concepts,
)

BROADER = "broader"
ALT_LABEL = "altLabel"
NOTATION = "notation"
EXACT_MATCH = "exactMatch"
LANGUAGE = "lang"
INCLUDE_RETIRED = "includeRetired"

QUERY_PROPERTY_NAMES = {
    BROADER: gettext_lazy("Broader concept (label or id)"),
    ALT_LABEL: gettext_lazy("Alternate label"),
    NOTATION: gettext_lazy("Identifier"),
    EXACT_MATCH: gettext_lazy("Exact match URI"),
    LANGUAGE: gettext_lazy("Label language"),
    INCLUDE_RETIRED: gettext_lazy("Include retired concepts"),
}
TRUE_VALUES = {"true", "1", "yes"}


def normalize_property_values(raw_value):
    """Flatten a property value (scalar, reconciled ``{"id": …}``, or list) to strings."""
    raw_values = raw_value if isinstance(raw_value, list) else [raw_value]
    normalized_values = []
    for value in raw_values:
        if isinstance(value, dict):
            value = value.get("id")
        if value is None:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        value_text = str(value).strip()
        if value_text:
            normalized_values.append(value_text)
    return normalized_values


def parse_query_properties(raw_properties):
    """Return ``{property_id: (value, …)}``; raise ValueError if malformed."""
    if raw_properties is None:
        return {}
    if not isinstance(raw_properties, list):
        raise ValueError(_('A query\'s "properties" must be a list.'))

    values_by_property_id = defaultdict(list)
    for raw_property in raw_properties:
        if not isinstance(raw_property, dict) or not isinstance(
            raw_property.get("pid"), str
        ):
            raise ValueError(_('Each query property needs a "pid" string.'))
        property_id = raw_property["pid"]
        if property_id not in QUERY_PROPERTY_NAMES:
            raise ValueError(
                _("Unknown query property: %(property_id)s")
                % {"property_id": property_id}
            )
        values_by_property_id[property_id].extend(
            normalize_property_values(raw_property.get("v"))
        )
    return {
        property_id: tuple(values)
        for property_id, values in values_by_property_id.items()
        if values
    }


def is_true_value(values):
    return bool(values) and values[0].casefold() in TRUE_VALUES


def find_concepts_by_notation(notations):
    """Return ``{notation: {concept_id, …}}`` for concepts with these identifiers."""
    concept_ids_by_notation = defaultdict(set)
    if not notations:
        return concept_ids_by_notation
    identifier_tiles = TileModel.objects.filter(
        nodegroup_id=IDENTIFIER_NODEGROUP,
        **{f"data__{IDENTIFIER_CONTENT_NODE}__in": list(notations)},
    ).values_list("resourceinstance_id", f"data__{IDENTIFIER_CONTENT_NODE}")
    for concept_id, notation in identifier_tiles:
        concept_ids_by_notation[notation].add(str(concept_id))
    return concept_ids_by_notation


def find_concepts_by_exact_match(uris):
    """Return ``{casefolded uri: {concept_id, …}}`` for concepts recorded as an
    exactMatch of each URI, or whose own URI it is."""
    concept_ids_by_uri = defaultdict(set)
    if not uris:
        return concept_ids_by_uri

    exact_match_relation_uri = get_list_item_tile_value(EXACT_MATCH_LIST_ITEM_ID)["uri"]
    matched_uri_tiles = TileModel.objects.filter(
        nodegroup_id=MATCH_STATUS_NODEGROUP,
        **{f"data__{MATCH_STATUS_RELATION_NODE}__0__uri": exact_match_relation_uri},
    ).filter(
        reduce(
            or_,
            (
                Q(**{f"data__{MATCH_STATUS_COMPARATE_NODE}__iexact": uri})
                for uri in uris
            ),
        )
    )
    own_uri_tiles = TileModel.objects.filter(nodegroup_id=URI_NODEGROUP).filter(
        reduce(or_, (Q(**{f"data__{URI_CONTENT_NODE}__iexact": uri}) for uri in uris))
    )
    for tiles, content_node in [
        (matched_uri_tiles, MATCH_STATUS_COMPARATE_NODE),
        (own_uri_tiles, URI_CONTENT_NODE),
    ]:
        for concept_id, uri in tiles.values_list(
            "resourceinstance_id", f"data__{content_node}"
        ):
            concept_ids_by_uri[uri.strip().casefold()].add(str(concept_id))
    return concept_ids_by_uri


def find_identified_concept_ids(queries_by_key):
    """Return ``{query_key: {concept_id, …}}`` for queries naming a notation or
    exactMatch, in lookups shared by the whole batch."""
    queries = queries_by_key.values()
    concept_ids_by_notation = find_concepts_by_notation(
        {notation for query in queries for notation in query.values_for(NOTATION)}
    )
    concept_ids_by_uri = find_concepts_by_exact_match(
        {uri for query in queries for uri in query.values_for(EXACT_MATCH)}
    )
    identified_concept_ids_by_key = {}
    for query_key, query in queries_by_key.items():
        identified_concept_ids = set()
        for notation in query.values_for(NOTATION):
            identified_concept_ids |= concept_ids_by_notation.get(notation, set())
        for uri in query.values_for(EXACT_MATCH):
            identified_concept_ids |= concept_ids_by_uri.get(uri.casefold(), set())
        identified_concept_ids_by_key[query_key] = identified_concept_ids
    return identified_concept_ids_by_key


@dataclass(frozen=True)
class PropertyEvidence:
    """What a concept offers for comparison with query property values."""

    broader_references: frozenset = frozenset()
    alternate_labels: frozenset = frozenset()


def gather_property_evidence(
    concept_ids, needs_broader, needs_alternate_labels, public_scheme_ids=None
):
    """Return ``{concept_id: PropertyEvidence}``, querying only what a batch uses.

    Broader references hold each broader concept's id and every one of its labels,
    casefolded, so a sheet column of broader terms matches in any language.
    """
    if not concept_ids or not (needs_broader or needs_alternate_labels):
        return {}

    broader_ids_by_concept_id = (
        get_public_broader_ids_for_concepts(concept_ids, public_scheme_ids)
        if needs_broader
        else {}
    )
    all_broader_ids = {
        broader_id
        for broader_ids in broader_ids_by_concept_id.values()
        for broader_id in broader_ids
    }
    labelled_concept_ids = all_broader_ids | (
        set(concept_ids) if needs_alternate_labels else set()
    )

    all_labels_by_concept_id = defaultdict(set)
    alternate_labels_by_concept_id = defaultdict(set)
    label_tiles = TileModel.objects.filter(
        nodegroup_id=CONCEPT_NAME_NODEGROUP,
        resourceinstance_id__in=labelled_concept_ids,
    ).values_list("resourceinstance_id", "data")
    for concept_id, tile_data in label_tiles:
        label = (tile_data.get(CONCEPT_NAME_CONTENT_NODE) or "").strip().casefold()
        all_labels_by_concept_id[str(concept_id)].add(label)
        label_types = tile_data.get(CONCEPT_NAME_TYPE_NODE) or []
        if label_types and label_types[0].get("uri") == ALT_LABEL_URI:
            alternate_labels_by_concept_id[str(concept_id)].add(label)

    evidence_by_concept_id = {}
    for concept_id in concept_ids:
        broader_references = set()
        for broader_id in broader_ids_by_concept_id.get(concept_id, []):
            broader_references.add(broader_id.casefold())
            broader_references |= all_labels_by_concept_id.get(broader_id, set())
        evidence_by_concept_id[concept_id] = PropertyEvidence(
            broader_references=frozenset(broader_references),
            alternate_labels=frozenset(
                alternate_labels_by_concept_id.get(concept_id, set())
            ),
        )
    return evidence_by_concept_id


def evaluate_query_properties(query, evidence, is_identified):
    """Return ``(matched_property_count, is_contradicted)`` for one candidate.

    A broader term that matches none of the candidate's broader concepts, or an
    identifier the candidate does not carry, contradicts it. A missing altLabel or
    exactMatch link does not: those are often simply unrecorded.
    """
    matched_property_count = 0
    is_contradicted = False

    broader_values = {value.casefold() for value in query.values_for(BROADER)}
    if broader_values:
        if broader_values & evidence.broader_references:
            matched_property_count += 1
        else:
            is_contradicted = True

    alternate_label_values = {value.casefold() for value in query.values_for(ALT_LABEL)}
    if alternate_label_values & evidence.alternate_labels:
        matched_property_count += 1

    if query.values_for(NOTATION) and not is_identified:
        is_contradicted = True

    return matched_property_count, is_contradicted
