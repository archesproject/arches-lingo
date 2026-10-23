"""A CSV of concepts for editors to reconcile against external authorities in
OpenRefine, then bring the matches back with the match-link import."""

import csv
from collections import defaultdict

from django.utils.translation import gettext as _

from arches.app.models.models import (
    ResourceInstance,
    ResourceInstanceLifecycleState,
    TileModel,
)

from arches_lingo.const import (
    ALT_LABEL_URI,
    CLOSE_MATCH_LIST_ITEM_ID,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_TYPE_NODE,
    CONCEPTS_GRAPH_ID,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    EXACT_MATCH_LIST_ITEM_ID,
    MATCH_STATUS_COMPARATE_NODE,
    MATCH_STATUS_NODEGROUP,
    MATCH_STATUS_RELATION_NODE,
    PREF_LABEL_URI,
    RELATED_MATCH_LIST_ITEM_ID,
)
from arches_lingo.models import ConceptSet
from arches_lingo.permissions import is_lingo_admin
from arches_lingo.utils.advanced_search import AdvancedSearchEvaluator
from arches_lingo.utils.concept_lifecycle import (
    RETIRED_STATE_ID,
    reasons_concepts_cannot_receive_data,
)
from arches_lingo.utils.concept_matching import get_scheme_ids_for_concepts
from arches_lingo.utils.concept_merge.tiles import get_list_item_tile_value
from arches_lingo.utils.reconciliation.concept_summaries import (
    get_broader_ids_for_concepts,
    get_display_labels_for_concepts,
)
from arches_lingo.utils.reconciliation.labels import (
    choose_display_label_tile,
    get_scheme_display_names,
    is_same_base_language,
)
from arches_lingo.utils.search_service import (
    get_identifiers_for_concepts,
    get_uris_for_concepts,
)

WORKSHEET_COLUMNS = [
    "concept_id",
    "uri",
    "identifier",
    "pref_label",
    "pref_label_language",
    "alt_labels",
    "broader_labels",
    "scheme",
    "lifecycle_state",
    "editable",
    "exact_matches",
    "close_matches",
    "related_matches",
    # Left empty for the editor to fill in OpenRefine, then read by the
    # match-link import.
    "match_uri",
    "match_type",
]
# OpenRefine splits these with "Split multi-valued cells".
MULTI_VALUE_SEPARATOR = "|"
WORKSHEET_BATCH_SIZE = 500
SCOPE_KEYS = ("scheme_id", "concept_set_id", "query")
MATCH_COLUMN_BY_LIST_ITEM_ID = {
    EXACT_MATCH_LIST_ITEM_ID: "exact_matches",
    CLOSE_MATCH_LIST_ITEM_ID: "close_matches",
    RELATED_MATCH_LIST_ITEM_ID: "related_matches",
}


def parse_worksheet_scope(request_body):
    """Return ``(scope_key, scope_value)``; raise ValueError unless exactly one is given."""
    scope = request_body.get("scope") if isinstance(request_body, dict) else None
    if not isinstance(scope, dict):
        raise ValueError(_('The request needs a "scope" object.'))
    given_scopes = [
        (scope_key, scope[scope_key])
        for scope_key in SCOPE_KEYS
        if scope.get(scope_key) not in (None, "")
    ]
    if len(given_scopes) != 1:
        raise ValueError(_("Give exactly one of scheme_id, concept_set_id or query."))
    return given_scopes[0]


def resolve_worksheet_concept_ids(scope_key, scope_value, user):
    """Return the ids of the non-retired concepts in scope, in a stable order."""
    if scope_key == "scheme_id":
        candidate_ids = TileModel.objects.filter(
            nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
            **{
                f"data__{CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}__contains": [
                    {"resourceId": str(scope_value)}
                ]
            },
        ).values("resourceinstance_id")
    elif scope_key == "concept_set_id":
        try:
            concept_set = ConceptSet.objects.get(pk=scope_value, user=user)
        except (ConceptSet.DoesNotExist, ValueError):
            raise ValueError(_("That concept set was not found."))
        candidate_ids = concept_set.members.values("concept_id")
    else:
        if not isinstance(scope_value, dict):
            raise ValueError(_("The search query must be an object."))
        candidate_ids = AdvancedSearchEvaluator(user=user).evaluate(scope_value)

    return [
        str(concept_id)
        for concept_id in ResourceInstance.objects.filter(
            pk__in=candidate_ids, graph_id=CONCEPTS_GRAPH_ID
        )
        .exclude(resource_instance_lifecycle_state_id=RETIRED_STATE_ID)
        .order_by("pk")
        .values_list("pk", flat=True)
    ]


def get_match_uris_by_column(concept_ids, column_by_relation_uri):
    """Return ``{concept_id: {column: [uri, …]}}`` for exact, close and related matches."""
    match_uris_by_column = defaultdict(lambda: defaultdict(list))
    match_tiles = TileModel.objects.filter(
        nodegroup_id=MATCH_STATUS_NODEGROUP, resourceinstance_id__in=concept_ids
    ).values_list("resourceinstance_id", "data")
    for concept_id, tile_data in match_tiles:
        relation_values = tile_data.get(MATCH_STATUS_RELATION_NODE) or []
        matched_uri = (tile_data.get(MATCH_STATUS_COMPARATE_NODE) or "").strip()
        column = column_by_relation_uri.get(
            relation_values[0].get("uri") if relation_values else None
        )
        if column and matched_uri:
            match_uris_by_column[str(concept_id)][column].append(matched_uri)
    return match_uris_by_column


def get_labels_for_worksheet(concept_ids, language):
    """Return ``{concept_id: (pref_label_tile, [alt labels in language])}``."""
    label_tiles_by_concept_id = defaultdict(list)
    for concept_id, tile_data in TileModel.objects.filter(
        nodegroup_id=CONCEPT_NAME_NODEGROUP, resourceinstance_id__in=concept_ids
    ).values_list("resourceinstance_id", "data"):
        if tile_data.get(CONCEPT_NAME_TYPE_NODE):
            label_tiles_by_concept_id[str(concept_id)].append(tile_data)

    labels_by_concept_id = {}
    for concept_id, label_tiles in label_tiles_by_concept_id.items():
        pref_label_tile = choose_display_label_tile(
            [
                label_tile
                for label_tile in label_tiles
                if label_tile[CONCEPT_NAME_TYPE_NODE][0].get("uri") == PREF_LABEL_URI
            ],
            CONCEPT_NAME_CONTENT_NODE,
            CONCEPT_NAME_TYPE_NODE,
            CONCEPT_NAME_LANGUAGE_NODE,
            language,
        )
        alternate_labels = sorted(
            label_tile[CONCEPT_NAME_CONTENT_NODE]
            for label_tile in label_tiles
            if label_tile[CONCEPT_NAME_TYPE_NODE][0].get("uri") == ALT_LABEL_URI
            and label_tile.get(CONCEPT_NAME_CONTENT_NODE)
            and is_same_base_language(
                label_tile.get(CONCEPT_NAME_LANGUAGE_NODE), language
            )
        )
        labels_by_concept_id[concept_id] = (pref_label_tile, alternate_labels)
    return labels_by_concept_id


def build_worksheet_rows(concept_ids, user, language, column_by_relation_uri):
    """Return one worksheet row per concept, in a fixed number of queries."""
    scheme_id_by_concept_id = get_scheme_ids_for_concepts(concept_ids)
    scheme_name_by_id = get_scheme_display_names(
        ResourceInstance.objects.filter(pk__in=set(scheme_id_by_concept_id.values())),
        language,
    )
    broader_ids_by_concept_id = get_broader_ids_for_concepts(concept_ids)
    broader_name_by_id = get_display_labels_for_concepts(
        {
            broader_id
            for broader_ids in broader_ids_by_concept_id.values()
            for broader_id in broader_ids
        },
        language,
    )
    labels_by_concept_id = get_labels_for_worksheet(concept_ids, language)
    uri_by_concept_id = get_uris_for_concepts(concept_ids)
    identifier_by_concept_id = get_identifiers_for_concepts(concept_ids)
    match_uris_by_concept_id = get_match_uris_by_column(
        concept_ids, column_by_relation_uri
    )
    cannot_receive_reason_by_concept_id = reasons_concepts_cannot_receive_data(
        concept_ids, scheme_id_by_concept_id, is_lingo_admin(user)
    )
    lifecycle_state_id_by_concept_id = {
        str(concept_id): lifecycle_state_id
        for concept_id, lifecycle_state_id in ResourceInstance.objects.filter(
            pk__in=concept_ids
        ).values_list("pk", "resource_instance_lifecycle_state_id")
    }
    lifecycle_state_name_by_id = {
        state_id: str(state_name)
        for state_id, state_name in ResourceInstanceLifecycleState.objects.filter(
            pk__in=set(lifecycle_state_id_by_concept_id.values())
        ).values_list("pk", "name")
    }

    rows = []
    for concept_id in concept_ids:
        pref_label_tile, alternate_labels = labels_by_concept_id.get(
            concept_id, (None, [])
        )
        match_uris = match_uris_by_concept_id.get(concept_id, {})
        rows.append(
            [
                concept_id,
                uri_by_concept_id.get(concept_id) or "",
                identifier_by_concept_id.get(concept_id) or "",
                pref_label_tile[CONCEPT_NAME_CONTENT_NODE] if pref_label_tile else "",
                pref_label_tile[CONCEPT_NAME_LANGUAGE_NODE] if pref_label_tile else "",
                MULTI_VALUE_SEPARATOR.join(alternate_labels),
                MULTI_VALUE_SEPARATOR.join(
                    sorted(
                        broader_name_by_id[broader_id]
                        for broader_id in broader_ids_by_concept_id.get(concept_id, [])
                        if broader_name_by_id.get(broader_id)
                    )
                ),
                scheme_name_by_id.get(scheme_id_by_concept_id.get(concept_id), ""),
                lifecycle_state_name_by_id.get(
                    lifecycle_state_id_by_concept_id.get(concept_id), ""
                ),
                (
                    "false"
                    if concept_id in cannot_receive_reason_by_concept_id
                    else "true"
                ),
                *(
                    MULTI_VALUE_SEPARATOR.join(sorted(match_uris.get(column, [])))
                    for column in MATCH_COLUMN_BY_LIST_ITEM_ID.values()
                ),
                "",
                "",
            ]
        )
    return rows


class EchoBuffer:
    """A file-like sink that hands each CSV line straight back for streaming."""

    def write(self, value):
        return value


def stream_worksheet(concept_ids, user, language):
    """Yield the worksheet CSV line by line, hydrating concepts in batches so a
    whole AAT-sized scheme is never held in memory at once."""
    csv_writer = csv.writer(EchoBuffer())
    column_by_relation_uri = {
        get_list_item_tile_value(list_item_id)["uri"]: column
        for list_item_id, column in MATCH_COLUMN_BY_LIST_ITEM_ID.items()
    }
    yield csv_writer.writerow(WORKSHEET_COLUMNS)
    for batch_start in range(0, len(concept_ids), WORKSHEET_BATCH_SIZE):
        batch_concept_ids = concept_ids[
            batch_start : batch_start + WORKSHEET_BATCH_SIZE
        ]
        for row in build_worksheet_rows(
            batch_concept_ids, user, language, column_by_relation_uri
        ):
            yield csv_writer.writerow(row)
