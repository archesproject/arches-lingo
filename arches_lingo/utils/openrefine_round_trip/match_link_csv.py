"""Reading a CSV of match links, typically a reconciliation worksheet that an
editor filled in with OpenRefine."""

import csv
import io

from django.utils import formats
from django.utils.translation import gettext as _

from arches_lingo.const import LINKABLE_MATCH_TYPES, MATCH_TYPE_EXACT
from arches_lingo.utils.openrefine_round_trip.worksheet_export import (
    MULTI_VALUE_SEPARATOR,
)
from arches_lingo.utils.reconciliation.labels import join_labels

MAX_IMPORT_LINKS = 10_000
MAX_IMPORT_BYTES = 5 * 1024 * 1024
REQUIRED_COLUMNS = ("concept_id", "match_uri")
SPREADSHEET_FIRST_DATA_ROW_NUMBER = 2

SKOS_NAMESPACE = "http://www.w3.org/2004/02/skos/core#"
MATCH_TYPE_BY_ALIAS = {
    f"{prefix}{match_type}".casefold(): match_type
    for match_type in LINKABLE_MATCH_TYPES
    for prefix in ("", "skos:", SKOS_NAMESPACE)
}


def normalize_column_name(column_name):
    return (column_name or "").strip().casefold().replace(" ", "_").replace("-", "_")


def canonical_match_type(raw_match_type):
    if not raw_match_type:
        return MATCH_TYPE_EXACT
    return MATCH_TYPE_BY_ALIAS.get(raw_match_type.casefold(), raw_match_type)


def parse_match_link_csv(uploaded_file):
    """Return ``[{row_number, concept_id, match_uri, match_type}]``.

    Columns other than concept_id, match_uri and match_type are ignored, so an
    edited reconciliation worksheet can be uploaded as it is. A match_uri cell
    holding several URIs gives one link per URI, and a row with none gives no
    link, so unmatched concepts neither show in the preview nor count toward
    MAX_IMPORT_LINKS. Raises ValueError for a file that cannot be read.
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
        return parse_match_links(csv.reader(io.StringIO(text)))
    except csv.Error as csv_error:
        raise ValueError(
            _("The file could not be read as a CSV: %(error)s") % {"error": csv_error}
        )


def parse_match_links(csv_reader):
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
            % {"columns": join_labels(missing_columns)}
        )

    def cell(row, column_name):
        column_index = column_index_by_name.get(column_name)
        if column_index is None or column_index >= len(row):
            return ""
        return row[column_index].strip()

    match_links = []
    for row_number, row in enumerate(
        csv_reader, start=SPREADSHEET_FIRST_DATA_ROW_NUMBER
    ):
        for match_uri in cell(row, "match_uri").split(MULTI_VALUE_SEPARATOR):
            if match_uri.strip():
                match_links.append(
                    {
                        "row_number": row_number,
                        "concept_id": cell(row, "concept_id"),
                        "match_uri": match_uri.strip(),
                        "match_type": canonical_match_type(cell(row, "match_type")),
                    }
                )
        if len(match_links) > MAX_IMPORT_LINKS:
            raise ValueError(
                _("The file has more than %(limit)s links.")
                % {
                    "limit": formats.number_format(
                        MAX_IMPORT_LINKS, force_grouping=True
                    )
                }
            )
    return match_links
