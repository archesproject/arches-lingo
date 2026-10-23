"""Import exactMatch/closeMatch/relatedMatch links from a CSV, typically one
reconciled against an external authority in OpenRefine.

The import only ever adds links: it never deletes or overwrites, and a link a
concept already records is skipped, so uploading the same file twice is harmless.
"""

import csv
import io
import logging
import uuid
from collections import Counter, defaultdict
from urllib.parse import urlsplit, urlunsplit

from django.db import transaction
from django.utils import formats, timezone
from django.utils.translation import get_language
from django.utils.translation import gettext as _

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
from arches_lingo.utils.concept_merge.tiles import (
    create_tile_on_concept,
    get_list_item_tile_value,
    load_concept_resources,
)
from arches_lingo.utils.openrefine_round_trip.worksheet_export import (
    MULTI_VALUE_SEPARATOR,
)
from arches_lingo.utils.reconciliation.concept_summaries import (
    get_display_labels_for_concepts,
)

logger = logging.getLogger(__name__)

MAX_IMPORT_ROWS = 10_000
MAX_IMPORT_BYTES = 5 * 1024 * 1024
REQUIRED_COLUMNS = ("concept_id", "match_uri")

SKOS_NAMESPACE = "http://www.w3.org/2004/02/skos/core#"
MATCH_TYPE_BY_ALIAS = {
    f"{prefix}{match_type}".casefold(): match_type
    for match_type in LINKABLE_MATCH_TYPES
    for prefix in ("", "skos:", SKOS_NAMESPACE)
}

OUTCOME_ADD = "add"
OUTCOME_ALREADY_LINKED = "already_linked"
# The concept and URI are already paired by another match type. SKOS makes some
# of these pairs contradictory (exactMatch and relatedMatch are disjoint), so an
# editor changes the type deliberately rather than the import adding a second.
OUTCOME_CONFLICTING_LINK = "conflicting_link"
OUTCOME_DUPLICATE_IN_FILE = "duplicate_in_file"
OUTCOME_UNKNOWN_CONCEPT = "unknown_concept"
OUTCOME_OUTSIDE_SCHEME = "outside_scheme"
OUTCOME_INVALID_MATCH_TYPE = "invalid_match_type"
OUTCOME_INVALID_URI = "invalid_uri"
OUTCOME_SELF_MATCH = "self_match"


def normalize_column_name(column_name):
    return (column_name or "").strip().casefold().replace(" ", "_").replace("-", "_")


def canonical_match_type(raw_match_type):
    """Accept exactMatch, skos:exactMatch or the full SKOS URI, in any case."""
    if not raw_match_type:
        return MATCH_TYPE_EXACT
    return MATCH_TYPE_BY_ALIAS.get(raw_match_type.casefold(), raw_match_type)


def parse_match_link_csv(uploaded_file):
    """Return ``[{row_number, concept_id, match_uri, match_type}]``.

    Headers match case-insensitively and columns other than concept_id,
    match_uri and match_type are ignored, so an edited reconciliation worksheet
    can be uploaded as it is. A match_uri cell holding several URIs joined the
    way the worksheet joins them gives one link per URI. Raises ValueError for
    a file that cannot be read.
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

    try:
        return parse_match_link_rows(csv.reader(io.StringIO(text)))
    except csv.Error as csv_error:
        raise ValueError(
            _("The file could not be read as a CSV: %(error)s") % {"error": csv_error}
        )


def parse_match_link_rows(csv_reader):
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
        match_uris = [
            match_uri.strip()
            for match_uri in cell(row, "match_uri").split(MULTI_VALUE_SEPARATOR)
            if match_uri.strip()
        ] or [""]
        for match_uri in match_uris:
            rows.append(
                {
                    "row_number": row_number,
                    "concept_id": cell(row, "concept_id"),
                    "match_uri": match_uri,
                    "match_type": canonical_match_type(cell(row, "match_type")),
                }
            )
        if len(rows) > MAX_IMPORT_ROWS:
            raise ValueError(
                _("The file has more than %(limit)s links.")
                % {"limit": formats.number_format(MAX_IMPORT_ROWS, force_grouping=True)}
            )
    return rows


def canonical_concept_id(raw_concept_id):
    try:
        return str(uuid.UUID(raw_concept_id))
    except (TypeError, ValueError):
        return None


def is_absolute_web_uri(uri):
    parsed_uri = urlsplit(uri)
    return (
        parsed_uri.scheme in ("http", "https")
        and bool(parsed_uri.netloc)
        and not any(character.isspace() for character in uri)
    )


def comparable_uri(uri):
    """Reduce a URI to what identifies its target, so http/https, host case and
    a trailing slash do not make the same link look new."""
    parsed_uri = urlsplit((uri or "").strip())
    return urlunsplit(
        (
            "",
            parsed_uri.netloc.casefold(),
            parsed_uri.path.rstrip("/"),
            parsed_uri.query,
            parsed_uri.fragment,
        )
    )


def stored_uri_variants(uri):
    """The common spellings of a URI that comparable_uri treats as the same,
    for finding it with an exact database lookup. Mixed-case hosts other than
    the one given are not enumerated."""
    parsed_uri = urlsplit(uri)
    path = parsed_uri.path.rstrip("/")
    return {
        urlunsplit(
            (
                scheme,
                host,
                path_variant,
                parsed_uri.query,
                parsed_uri.fragment,
            )
        )
        for scheme in ("http", "https")
        for host in (parsed_uri.netloc, parsed_uri.netloc.casefold())
        for path_variant in (path, f"{path}/")
    }


def uri_node_value_as_text(uri_node_value):
    """Older data may hold a URI as a url datatype value rather than a string."""
    if isinstance(uri_node_value, dict):
        return uri_node_value.get("url") or ""
    return uri_node_value if isinstance(uri_node_value, str) else ""


def get_own_uris(concept_ids):
    """Return ``{concept_id: {comparable uri, …}}``; a concept may have several."""
    own_uris_by_concept_id = defaultdict(set)
    for concept_id, uri_node_value in TileModel.objects.filter(
        nodegroup_id=URI_NODEGROUP, resourceinstance_id__in=concept_ids
    ).values_list("resourceinstance_id", f"data__{URI_CONTENT_NODE}"):
        uri = uri_node_value_as_text(uri_node_value)
        if uri:
            own_uris_by_concept_id[str(concept_id)].add(comparable_uri(uri))
    return own_uris_by_concept_id


def get_existing_links(concept_ids):
    """Return ``{(concept_id, comparable matched uri): {relation_uri, …}}``."""
    relation_uris_by_link = defaultdict(set)
    for concept_id, tile_data in TileModel.objects.filter(
        nodegroup_id=MATCH_STATUS_NODEGROUP, resourceinstance_id__in=concept_ids
    ).values_list("resourceinstance_id", "data"):
        relation_values = tile_data.get(MATCH_STATUS_RELATION_NODE) or []
        if relation_values:
            relation_uris_by_link[
                (
                    str(concept_id),
                    comparable_uri(tile_data.get(MATCH_STATUS_COMPARATE_NODE)),
                )
            ].add(relation_values[0].get("uri"))
    return relation_uris_by_link


def outcome_for_known_link(relation_uri, recorded_relation_uris, same_type_outcome):
    if relation_uri in recorded_relation_uris:
        return same_type_outcome
    return OUTCOME_CONFLICTING_LINK


def get_internal_concept_uris(match_uris):
    """Return the comparable forms of these URIs that belong to concepts here."""
    return {
        comparable_uri(uri_node_value_as_text(internal_uri))
        for internal_uri in TileModel.objects.filter(
            nodegroup_id=URI_NODEGROUP,
            **{
                f"data__{URI_CONTENT_NODE}__in": [
                    uri_variant
                    for match_uri in match_uris
                    for uri_variant in stored_uri_variants(match_uri)
                ]
            },
        ).values_list(f"data__{URI_CONTENT_NODE}", flat=True)
    }


def validate_match_link_rows(rows, user, scheme_id=None):
    """Give each row an ``outcome``, in a fixed number of queries.

    Writability uses the same rule as the concept matching "link" action. With
    a ``scheme_id``, concepts in other schemes are left alone. A match URI that
    belongs to another concept here is still added (one way only) and flagged
    ``is_internal_concept``: a two-way link between Lingo concepts belongs to
    the concept matches workflow.
    """
    concept_ids = [canonical_concept_id(row["concept_id"]) for row in rows]
    existing_concept_ids = {
        str(concept_id)
        for concept_id in ResourceInstance.objects.filter(
            pk__in={concept_id for concept_id in concept_ids if concept_id},
            graph_id=CONCEPTS_GRAPH_ID,
        ).values_list("pk", flat=True)
    }
    scheme_id_by_concept_id = get_scheme_ids_for_concepts(existing_concept_ids)
    cannot_receive_reason_by_concept_id = reasons_concepts_cannot_receive_data(
        existing_concept_ids,
        scheme_id_by_concept_id,
        user is not None and is_lingo_admin(user),
    )
    own_uris_by_concept_id = get_own_uris(existing_concept_ids)
    existing_relation_uris_by_link = get_existing_links(existing_concept_ids)
    relation_uri_by_match_type = {
        match_type: get_list_item_tile_value(list_item_id)["uri"]
        for match_type, list_item_id in LINKABLE_MATCH_TYPES.items()
    }
    internal_concept_uris = get_internal_concept_uris(
        {row["match_uri"] for row in rows if is_absolute_web_uri(row["match_uri"])}
    )

    relation_uris_by_link_seen_in_file = defaultdict(set)
    validated_rows = []
    for row, concept_id in zip(rows, concept_ids):
        match_uri = comparable_uri(row["match_uri"])
        link = (concept_id, match_uri)
        relation_uri = relation_uri_by_match_type.get(row["match_type"])
        if concept_id not in existing_concept_ids:
            outcome = OUTCOME_UNKNOWN_CONCEPT
        elif scheme_id and scheme_id_by_concept_id.get(concept_id) != str(scheme_id):
            outcome = OUTCOME_OUTSIDE_SCHEME
        elif row["match_type"] not in LINKABLE_MATCH_TYPES:
            outcome = OUTCOME_INVALID_MATCH_TYPE
        elif not is_absolute_web_uri(row["match_uri"]):
            outcome = OUTCOME_INVALID_URI
        elif match_uri in own_uris_by_concept_id.get(concept_id, set()):
            outcome = OUTCOME_SELF_MATCH
        elif link in relation_uris_by_link_seen_in_file:
            outcome = outcome_for_known_link(
                relation_uri,
                relation_uris_by_link_seen_in_file[link],
                OUTCOME_DUPLICATE_IN_FILE,
            )
        elif concept_id in cannot_receive_reason_by_concept_id:
            outcome = cannot_receive_reason_by_concept_id[concept_id]
        elif link in existing_relation_uris_by_link:
            outcome = outcome_for_known_link(
                relation_uri,
                existing_relation_uris_by_link[link],
                OUTCOME_ALREADY_LINKED,
            )
        else:
            outcome = OUTCOME_ADD
        if relation_uri and outcome not in (
            OUTCOME_UNKNOWN_CONCEPT,
            OUTCOME_OUTSIDE_SCHEME,
            OUTCOME_INVALID_URI,
            OUTCOME_SELF_MATCH,
        ):
            relation_uris_by_link_seen_in_file[link].add(relation_uri)
        validated_rows.append(
            {
                **row,
                "concept_id": concept_id or row["concept_id"],
                "outcome": outcome,
                "is_internal_concept": match_uri in internal_concept_uris,
            }
        )
    return validated_rows


def count_outcomes(validated_rows):
    return dict(Counter(validated_row["outcome"] for validated_row in validated_rows))


def preview_match_link_import(uploaded_file, user, scheme_id=None):
    """Validate an upload without writing anything."""
    validated_rows = validate_match_link_rows(
        parse_match_link_csv(uploaded_file), user, scheme_id
    )
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


def claim_match_link_import(match_link_import):
    """Move a pending import to running; False if it was already taken or
    given up on, so a late or repeated worker never applies it a second time."""
    started = timezone.now()
    is_claimed = MatchLinkImport.objects.filter(
        pk=match_link_import.pk, status=MatchLinkImport.STATUS_PENDING
    ).update(status=MatchLinkImport.STATUS_RUNNING, started=started)
    match_link_import.refresh_from_db()
    return bool(is_claimed)


def lock_concepts_in_rows(rows):
    """Lock the rows' concepts until the transaction ends, so two imports
    running at once cannot both decide the same link is new."""
    concept_ids = {canonical_concept_id(row.get("concept_id")) for row in rows}
    list(
        ResourceInstance.objects.select_for_update()
        .filter(pk__in=concept_ids - {None})
        .order_by("pk")
        .values_list("pk", flat=True)
    )


def apply_match_link_import(match_link_import):
    """Validate the stored rows again (state may have changed since the
    preview) and write the links in one edit transaction.

    The record is saved as soon as the links commit, so its
    ``edit_transaction_id`` survives a failure while indexing them.
    """
    if not claim_match_link_import(match_link_import):
        logger.warning(
            "Match link import %s is %s, not pending; not applying it.",
            match_link_import.pk,
            match_link_import.status,
        )
        return match_link_import
    edit_transaction_id = uuid.uuid4()
    rows_to_add = []
    try:
        relation_tile_value_by_match_type = {
            match_type: get_list_item_tile_value(list_item_id)
            for match_type, list_item_id in LINKABLE_MATCH_TYPES.items()
        }
        with transaction.atomic():
            lock_concepts_in_rows(match_link_import.rows)
            validated_rows = validate_match_link_rows(
                match_link_import.rows,
                match_link_import.user,
                match_link_import.scheme_id,
            )
            rows_to_add = [
                validated_row
                for validated_row in validated_rows
                if validated_row["outcome"] == OUTCOME_ADD
            ]
            resource_by_concept_id = load_concept_resources(
                *{row_to_add["concept_id"] for row_to_add in rows_to_add}
            )
            for row_to_add in rows_to_add:
                create_tile_on_concept(
                    row_to_add["concept_id"],
                    MATCH_STATUS_NODEGROUP,
                    {
                        MATCH_STATUS_RELATION_NODE: [
                            relation_tile_value_by_match_type[row_to_add["match_type"]]
                        ],
                        MATCH_STATUS_COMPARATE_NODE: row_to_add["match_uri"],
                    },
                    None,
                    edit_transaction_id,
                    resource_by_concept_id[row_to_add["concept_id"]],
                )
        if rows_to_add:
            match_link_import.edit_transaction_id = edit_transaction_id
        match_link_import.outcome_counts = count_outcomes(validated_rows)
        match_link_import.status = MatchLinkImport.STATUS_COMPLETE
    except Exception:
        logger.exception("Match link import %s failed", match_link_import.pk)
        match_link_import.status = MatchLinkImport.STATUS_FAILED
        match_link_import.error_code = MatchLinkImport.ERROR_APPLY_FAILED
    match_link_import.finished = timezone.now()
    match_link_import.save()

    if match_link_import.status == MatchLinkImport.STATUS_COMPLETE and rows_to_add:
        try:
            index_concepts_in_transaction(edit_transaction_id)
        except Exception:
            logger.exception(
                "Match link import %s could not index its concepts",
                match_link_import.pk,
            )
            match_link_import.error_code = MatchLinkImport.ERROR_INDEXING_FAILED
            match_link_import.save(update_fields=["error_code"])
    return match_link_import
