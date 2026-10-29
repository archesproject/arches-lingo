"""A CSV of concepts for editors to reconcile against external authorities in
OpenRefine, then bring the matches back with the match-link import."""

import csv
import io
import uuid
from collections import defaultdict

from django.conf import settings
from django.utils import formats, translation
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from arches.app.models.models import (
    Language,
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
# The worksheet is built in full before it is sent, so a failure part way
# through is an error response rather than a truncated file that looks whole.
# Built within the request, so kept small enough to finish well inside a proxy
# timeout; it also matches the match-link import's row limit.
MAX_WORKSHEET_CONCEPTS = getattr(
    settings, "LINGO_RECONCILIATION_WORKSHEET_MAX_CONCEPTS", 10_000
)
# Cells that a spreadsheet would run as a formula get a leading apostrophe;
# stored URIs are not guaranteed to be web addresses, so no column is exempt.
# A leading "-" is left alone: labels such as "-ism" are plausible, and labels
# are what OpenRefine sends to the external authority.
FORMULA_TRIGGER_CHARACTERS = ("=", "+", "@", "\t", "\r")
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


def is_empty_search_query(query):
    return "facet" not in query and not query.get("conditions")


def resolve_worksheet_concept_ids(scope_key, scope_value, user):
    """Return the ids of the non-retired concepts in scope, in a stable order."""
    if scope_key == "scheme_id":
        try:
            scope_value = uuid.UUID(str(scope_value))
        except ValueError:
            raise ValueError(_("The scheme id is not valid."))
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
        except (ConceptSet.DoesNotExist, TypeError, ValueError):
            raise ValueError(_("That concept set was not found."))
        candidate_ids = concept_set.members.values("concept_id")
    else:
        if not isinstance(scope_value, dict):
            raise ValueError(_("The search query must be an object."))
        if is_empty_search_query(scope_value):
            raise ValueError(_("Add at least one search condition."))
        candidate_ids = AdvancedSearchEvaluator(user=user).evaluate(scope_value)

    concept_ids = [
        str(concept_id)
        for concept_id in ResourceInstance.objects.filter(
            pk__in=candidate_ids, graph_id=CONCEPTS_GRAPH_ID
        )
        .exclude(resource_instance_lifecycle_state_id=RETIRED_STATE_ID)
        .order_by("pk")
        .values_list("pk", flat=True)[: MAX_WORKSHEET_CONCEPTS + 1]
    ]
    if len(concept_ids) > MAX_WORKSHEET_CONCEPTS:
        raise ValueError(
            _(
                "A worksheet can hold at most %(limit)s concepts. "
                "Narrow the scheme, set or search and try again."
            )
            % {
                "limit": formats.number_format(
                    MAX_WORKSHEET_CONCEPTS, force_grouping=True
                )
            }
        )
    return concept_ids


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


def neutralize_formula(cell_value):
    if isinstance(cell_value, str) and cell_value.startswith(
        FORMULA_TRIGGER_CHARACTERS
    ):
        return f"'{cell_value}"
    return cell_value


def resolve_worksheet_language(requested_language):
    """Return the requested label language if Arches knows it, else the
    active one, so an arbitrary value never reaches translation.override."""
    if (
        isinstance(requested_language, str)
        and Language.objects.filter(code=requested_language).exists()
    ):
        return requested_language
    return get_language() or settings.LANGUAGE_CODE


def write_worksheet(concept_ids, user, language):
    """Return the worksheet CSV, hydrating concepts in batches so each query
    stays a manageable size."""
    worksheet = io.StringIO()
    csv_writer = csv.writer(worksheet)
    column_by_relation_uri = {
        get_list_item_tile_value(list_item_id)["uri"]: column
        for list_item_id, column in MATCH_COLUMN_BY_LIST_ITEM_ID.items()
    }
    csv_writer.writerow(WORKSHEET_COLUMNS)
    # Lifecycle state names are translated fields, read in the active language.
    with translation.override(language):
        for batch_start in range(0, len(concept_ids), WORKSHEET_BATCH_SIZE):
            batch_concept_ids = concept_ids[
                batch_start : batch_start + WORKSHEET_BATCH_SIZE
            ]
            for row in build_worksheet_rows(
                batch_concept_ids, user, language, column_by_relation_uri
            ):
                csv_writer.writerow(
                    [neutralize_formula(cell_value) for cell_value in row]
                )
    return worksheet.getvalue()
