"""Import exactMatch/closeMatch/relatedMatch links from a CSV, typically one
reconciled against an external authority in OpenRefine.

The import only ever adds links: it never deletes or overwrites, and a link a
concept already records is skipped, so uploading the same file twice is harmless.
"""

import csv
import io
import logging
import uuid
from collections import Counter
from urllib.parse import urlsplit

from django.db import transaction
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext as _

import arches.app.utils.task_management as task_management
from arches.app.models.models import ResourceInstance, TileModel

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    LINKABLE_MATCH_TYPES,
    MATCH_STATUS_COMPARATE_NODE,
    MATCH_STATUS_NODEGROUP,
    MATCH_STATUS_RELATION_NODE,
    MATCH_TYPE_EXACT,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)
from arches_lingo.models import MatchLinkImport
from arches_lingo.permissions import is_lingo_admin
from arches_lingo.utils.concept_lifecycle import (
    index_concepts_in_transaction,
    reasons_concepts_cannot_receive_data,
)
from arches_lingo.utils.concept_matching import get_scheme_ids_for_concepts
from arches_lingo.utils.concept_merge.rules import ConceptMergeGraph
from arches_lingo.utils.concept_merge.tiles import (
    get_list_item_tile_value,
    load_concept_resources,
    write_match_tile,
)
from arches_lingo.utils.reconciliation.concept_summaries import (
    get_display_labels_for_concepts,
)

logger = logging.getLogger(__name__)

MAX_IMPORT_ROWS = 10_000
MAX_IMPORT_BYTES = 5 * 1024 * 1024
REQUIRED_COLUMNS = ("concept_id", "match_uri")

OUTCOME_ADD = "add"
OUTCOME_ALREADY_LINKED = "already_linked"
OUTCOME_DUPLICATE_IN_FILE = "duplicate_in_file"
OUTCOME_UNKNOWN_CONCEPT = "unknown_concept"
OUTCOME_INVALID_MATCH_TYPE = "invalid_match_type"
OUTCOME_INVALID_URI = "invalid_uri"
OUTCOME_SELF_MATCH = "self_match"
# The same values reasons_concepts_cannot_receive_data reports.
OUTCOME_NOT_EDITABLE = "not_editable"
OUTCOME_SCHEME_LOCKED = "scheme_locked"


def normalize_column_name(column_name):
    return (column_name or "").strip().casefold().replace(" ", "_").replace("-", "_")


def parse_match_link_csv(uploaded_file):
    """Return ``[{row_number, concept_id, match_uri, match_type}]``.

    Headers match case-insensitively and columns other than concept_id,
    match_uri and match_type are ignored, so an edited reconciliation worksheet
    can be uploaded as it is. Raises ValueError for a file that cannot be read.
    """
    if uploaded_file is None:
        raise ValueError(_("Choose a CSV file to import."))
    if uploaded_file.size > MAX_IMPORT_BYTES:
        raise ValueError(
            _("The file is larger than %(limit)s MB.")
            % {"limit": MAX_IMPORT_BYTES // (1024 * 1024)}
        )
    try:
        text = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError(_("The file must be a UTF-8 encoded CSV."))

    csv_reader = csv.reader(io.StringIO(text))
    header = next(csv_reader, None)
    if header is None:
        raise ValueError(_("The file is empty."))
    column_index_by_name = {
        normalize_column_name(column_name): column_index
        for column_index, column_name in enumerate(header)
    }
    missing_columns = [
        column_name
        for column_name in REQUIRED_COLUMNS
        if column_name not in column_index_by_name
    ]
    if missing_columns:
        raise ValueError(
            _("The file needs these columns: %(columns)s.")
            % {"columns": ", ".join(missing_columns)}
        )

    def cell(row, column_name):
        column_index = column_index_by_name.get(column_name)
        if column_index is None or column_index >= len(row):
            return ""
        return row[column_index].strip()

    rows = []
    # Line 1 is the header, so data rows are numbered as a spreadsheet shows them.
    for row_number, row in enumerate(csv_reader, start=2):
        if not any(value.strip() for value in row):
            continue
        rows.append(
            {
                "row_number": row_number,
                "concept_id": cell(row, "concept_id"),
                "match_uri": cell(row, "match_uri"),
                "match_type": cell(row, "match_type") or MATCH_TYPE_EXACT,
            }
        )
        if len(rows) > MAX_IMPORT_ROWS:
            raise ValueError(
                _("The file has more than %(limit)s rows.")
                % {"limit": f"{MAX_IMPORT_ROWS:,}"}
            )
    return rows


def canonical_concept_id(raw_concept_id):
    try:
        return str(uuid.UUID(raw_concept_id))
    except ValueError:
        return None


def is_absolute_web_uri(uri):
    parsed_uri = urlsplit(uri)
    return (
        parsed_uri.scheme in ("http", "https")
        and bool(parsed_uri.netloc)
        and not any(character.isspace() for character in uri)
    )


def get_own_uris(concept_ids):
    return {
        str(concept_id): (uri or "").strip()
        for concept_id, uri in TileModel.objects.filter(
            nodegroup_id=URI_NODEGROUP, resourceinstance_id__in=concept_ids
        ).values_list("resourceinstance_id", f"data__{URI_CONTENT_NODE}")
    }


def get_existing_links(concept_ids):
    """Return ``{(concept_id, relation_uri, matched_uri)}`` already recorded."""
    existing_links = set()
    for concept_id, tile_data in TileModel.objects.filter(
        nodegroup_id=MATCH_STATUS_NODEGROUP, resourceinstance_id__in=concept_ids
    ).values_list("resourceinstance_id", "data"):
        relation_values = tile_data.get(MATCH_STATUS_RELATION_NODE) or []
        if relation_values:
            existing_links.add(
                (
                    str(concept_id),
                    relation_values[0].get("uri"),
                    (tile_data.get(MATCH_STATUS_COMPARATE_NODE) or "").strip(),
                )
            )
    return existing_links


def get_internal_concept_uris(match_uris):
    """Return the subset of these URIs that belong to concepts in this instance."""
    return set(
        TileModel.objects.filter(
            nodegroup_id=URI_NODEGROUP,
            **{f"data__{URI_CONTENT_NODE}__in": list(match_uris)},
        ).values_list(f"data__{URI_CONTENT_NODE}", flat=True)
    )


def validate_match_link_rows(rows, user):
    """Give each row an ``outcome``, in a fixed number of queries.

    Writability uses the same rule as the concept matching "link" action. A
    match URI that belongs to another concept here is still added (one way
    only) and flagged ``is_internal_concept``: a two-way link between Lingo
    concepts belongs to the concept matches workflow.
    """
    concept_id_by_row_number = {
        row["row_number"]: canonical_concept_id(row["concept_id"]) for row in rows
    }
    candidate_concept_ids = {
        concept_id for concept_id in concept_id_by_row_number.values() if concept_id
    }
    existing_concept_ids = {
        str(concept_id)
        for concept_id in ResourceInstance.objects.filter(
            pk__in=candidate_concept_ids, graph_id=CONCEPTS_GRAPH_ID
        ).values_list("pk", flat=True)
    }
    cannot_receive_reason_by_concept_id = reasons_concepts_cannot_receive_data(
        existing_concept_ids,
        get_scheme_ids_for_concepts(existing_concept_ids),
        is_lingo_admin(user),
    )
    own_uri_by_concept_id = get_own_uris(existing_concept_ids)
    existing_links = get_existing_links(existing_concept_ids)
    relation_uri_by_match_type = {
        match_type: get_list_item_tile_value(list_item_id)["uri"]
        for match_type, list_item_id in LINKABLE_MATCH_TYPES.items()
    }
    internal_concept_uris = get_internal_concept_uris(
        {row["match_uri"] for row in rows if row["match_uri"]}
    )

    seen_links = set()
    validated_rows = []
    for row in rows:
        concept_id = concept_id_by_row_number[row["row_number"]]
        link = (
            concept_id,
            relation_uri_by_match_type.get(row["match_type"]),
            row["match_uri"],
        )
        if concept_id not in existing_concept_ids:
            outcome = OUTCOME_UNKNOWN_CONCEPT
        elif row["match_type"] not in LINKABLE_MATCH_TYPES:
            outcome = OUTCOME_INVALID_MATCH_TYPE
        elif not is_absolute_web_uri(row["match_uri"]):
            outcome = OUTCOME_INVALID_URI
        elif row["match_uri"] == own_uri_by_concept_id.get(concept_id):
            outcome = OUTCOME_SELF_MATCH
        elif link in seen_links:
            outcome = OUTCOME_DUPLICATE_IN_FILE
        elif concept_id in cannot_receive_reason_by_concept_id:
            outcome = cannot_receive_reason_by_concept_id[concept_id]
        elif link in existing_links:
            outcome = OUTCOME_ALREADY_LINKED
        else:
            outcome = OUTCOME_ADD
        seen_links.add(link)
        validated_rows.append(
            {
                **row,
                "concept_id": concept_id or row["concept_id"],
                "outcome": outcome,
                "is_internal_concept": row["match_uri"] in internal_concept_uris,
            }
        )
    return validated_rows


def count_outcomes(validated_rows):
    return dict(Counter(validated_row["outcome"] for validated_row in validated_rows))


def preview_match_link_import(uploaded_file, user):
    """Validate an upload without writing anything."""
    validated_rows = validate_match_link_rows(parse_match_link_csv(uploaded_file), user)
    concept_label_by_id = get_display_labels_for_concepts(
        {
            validated_row["concept_id"]
            for validated_row in validated_rows
            if validated_row["outcome"] != OUTCOME_UNKNOWN_CONCEPT
        },
        get_language(),
    )
    return {
        "total_rows": len(validated_rows),
        "counts_by_outcome": count_outcomes(validated_rows),
        "rows": [
            {
                **validated_row,
                "concept_label": concept_label_by_id.get(validated_row["concept_id"]),
            }
            for validated_row in validated_rows
        ],
    }


def start_match_link_import(uploaded_file, user):
    """Record an import and apply it on a worker, or right away without one."""
    rows = parse_match_link_csv(uploaded_file)
    match_link_import = MatchLinkImport.objects.create(
        user=user if user.is_authenticated else None,
        filename=(uploaded_file.name or "")[:255],
        rows=rows,
    )
    if task_management.check_if_celery_available():
        # Imported here only to break the tasks → this module → tasks cycle.
        from arches_lingo.tasks import apply_match_link_import_task

        apply_match_link_import_task.apply_async(args=[match_link_import.pk])
    else:
        apply_match_link_import(match_link_import)
    return match_link_import


def apply_match_link_import(match_link_import):
    """Validate the stored rows again (state may have changed since the
    preview) and write the links in one edit transaction."""
    match_link_import.status = MatchLinkImport.STATUS_RUNNING
    match_link_import.save(update_fields=["status"])
    try:
        validated_rows = validate_match_link_rows(
            match_link_import.rows, match_link_import.user
        )
        rows_to_add = [
            validated_row
            for validated_row in validated_rows
            if validated_row["outcome"] == OUTCOME_ADD
        ]
        edit_transaction_id = uuid.uuid4()
        relation_tile_value_by_match_type = {
            match_type: get_list_item_tile_value(list_item_id)
            for match_type, list_item_id in LINKABLE_MATCH_TYPES.items()
        }
        with transaction.atomic():
            resource_by_concept_id = load_concept_resources(
                *{row_to_add["concept_id"] for row_to_add in rows_to_add}
            )
            merge_graph = ConceptMergeGraph()
            for row_to_add in rows_to_add:
                write_match_tile(
                    resource_by_concept_id[row_to_add["concept_id"]],
                    row_to_add["match_uri"],
                    relation_tile_value_by_match_type[row_to_add["match_type"]],
                    edit_transaction_id,
                    merge_graph,
                )
        if rows_to_add:
            index_concepts_in_transaction(edit_transaction_id)
            match_link_import.edit_transaction_id = edit_transaction_id
        match_link_import.outcome_counts = count_outcomes(validated_rows)
        match_link_import.status = MatchLinkImport.STATUS_COMPLETE
    except Exception as error:
        logger.exception("Match link import %s failed", match_link_import.pk)
        match_link_import.status = MatchLinkImport.STATUS_FAILED
        match_link_import.error_message = str(error)
    match_link_import.finished = timezone.now()
    match_link_import.save()
    return match_link_import


def serialize_match_link_import(match_link_import):
    return {
        "id": match_link_import.pk,
        "filename": match_link_import.filename,
        "status": match_link_import.status,
        "created": match_link_import.created.isoformat(),
        "finished": (
            match_link_import.finished.isoformat()
            if match_link_import.finished
            else None
        ),
        "total_rows": len(match_link_import.rows),
        "outcome_counts": match_link_import.outcome_counts,
        "error_message": match_link_import.error_message,
    }
