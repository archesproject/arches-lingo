"""Export and restore a portable, compressed snapshot of all arches-lingo
concept/scheme resource data.

A concept or scheme resource does not stand alone: its tiles can point to
other resources for attribution and provenance (person_system, group,
textual_work) and for concept images (digital_object_system). To keep an
exported snapshot self-contained and restorable on its own, this module
gathers rows for the concept/scheme graphs *and* every graph they can
reference, plus the arches-lingo-specific per-scheme records (identifier
counters, URI templates, and attribution statements) that live outside the
tile data, plus the arches-core `ResourceIdentifier` rows those resources
have accumulated.

Performance: rather than Django's `dumpdata`/`loaddata` (which serializes and
saves every row individually through the ORM), this module streams data
directly to/from PostgreSQL with `COPY`, filtered by the target graphs. This
is dramatically faster and lighter on memory for large datasets, and the
resulting CSV is far more compact than the equivalent JSON fixture. Every
foreign key involved in these tables is `DEFERRABLE INITIALLY DEFERRED`, so
restore runs as a single transaction with constraint checks deferred to
COMMIT: table load order does not matter, and a failure partway through rolls
back cleanly instead of leaving partial data.

Storage: both the combined archive and the extracted uploaded files are
read/written through Django's configured default file storage
(`django.core.files.storage.default_storage`), so pointing
`ARCHES_STORAGEBACKEND` at S3 (or any other configured backend) is enough to
push/pull these snapshots to an existing bucket instead of local disk -- no
separate upload/download code is needed here.

Resource edit history (EditLog) is intentionally excluded: it is large, not
required to reconstruct the current state of the data, and tied to
user/transaction records that may not exist in the target environment.

Graph, node, nodegroup, card, widget, and controlled-list/list-item
definitions are also excluded. These are package metadata that should already
be present after installing/migrating the arches-lingo package, not data that
changes per-deployment. If your controlled lists (identifier types,
namespaces, mapping properties, etc.) have been customized beyond the
arches-lingo package defaults, those customizations must be migrated
separately, or referenced list items will not resolve after restore.
"""

import csv
import tarfile
import tempfile
from dataclasses import dataclass

from django.core.files.base import ContentFile, File as DjangoFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.db import connection, transaction

from arches.app.models.models import (
    File,
    GraphModel,
    ResourceInstance,
    ResourceIdentifier,
    ResourceXResource,
    TileModel,
)

from arches_lingo.const import LINGO_FIXTURE_GRAPH_SLUGS
from arches_lingo.models import (
    ConceptIdentifierCounter,
    SchemeAttribution,
    SchemeURITemplate,
)

DEFAULT_FIXTURE_STORAGE_KEY = "lingo_fixtures/lingo_concept_scheme_fixture.tar.gz"

# Every table's row set is scoped to the target graphs by filtering (directly
# or through a join) on this subquery, so a single `graph_ids` array parameter
# drives every COPY TO statement.
_GRAPH_FILTERED_RESOURCE_IDS_SQL = "SELECT resourceinstanceid FROM resource_instances WHERE graphid = ANY(%(graph_ids)s)"


@dataclass(frozen=True)
class FixtureTable:
    model: type
    where_sql: str
    # Bigint identity-column tables need their sequence bumped after a COPY
    # restores explicit id values, or the next ORM-created row will collide.
    identity_column: str | None = None

    @property
    def name(self):
        return self.model._meta.db_table

    @property
    def columns(self):
        # Derive the column list from the model at runtime rather than
        # hard-coding it, so it stays in sync with the model definition. The
        # resulting order is only used when writing an archive; on load the
        # column order is read back from the CSV header, because model field
        # declaration order (and therefore this order) can differ between
        # arches versions.
        return tuple(field.column for field in self.model._meta.concrete_fields)


FIXTURE_TABLES: tuple[FixtureTable, ...] = (
    FixtureTable(
        model=ResourceInstance,
        where_sql="graphid = ANY(%(graph_ids)s)",
    ),
    FixtureTable(
        model=TileModel,
        where_sql=f"resourceinstanceid IN ({_GRAPH_FILTERED_RESOURCE_IDS_SQL})",
    ),
    FixtureTable(
        model=File,
        where_sql=(
            "tileid IN (SELECT tileid FROM tiles WHERE resourceinstanceid IN "
            f"({_GRAPH_FILTERED_RESOURCE_IDS_SQL}))"
        ),
    ),
    FixtureTable(
        model=ResourceXResource,
        where_sql=(
            "resourceinstancefrom_graphid = ANY(%(graph_ids)s) "
            "OR resourceinstanceto_graphid = ANY(%(graph_ids)s)"
        ),
    ),
    FixtureTable(
        model=ResourceIdentifier,
        where_sql=f"resourceid_id IN ({_GRAPH_FILTERED_RESOURCE_IDS_SQL})",
        identity_column="id",
    ),
    FixtureTable(
        model=ConceptIdentifierCounter,
        where_sql=f"scheme_resource_instance_id IN ({_GRAPH_FILTERED_RESOURCE_IDS_SQL})",
        identity_column="id",
    ),
    FixtureTable(
        model=SchemeURITemplate,
        where_sql=f"scheme_resource_instance_id IN ({_GRAPH_FILTERED_RESOURCE_IDS_SQL})",
        identity_column="id",
    ),
    FixtureTable(
        model=SchemeAttribution,
        where_sql=f"scheme_resource_instance_id IN ({_GRAPH_FILTERED_RESOURCE_IDS_SQL})",
        identity_column="id",
    ),
)


def get_lingo_fixture_graph_ids():
    graphs_by_slug = {
        graph.slug: graph.graphid
        for graph in GraphModel.objects.filter(slug__in=LINGO_FIXTURE_GRAPH_SLUGS)
    }
    missing_slugs = set(LINGO_FIXTURE_GRAPH_SLUGS) - set(graphs_by_slug)
    if missing_slugs:
        raise LookupError(
            "The following expected arches-lingo graphs were not found: "
            f"{', '.join(sorted(missing_slugs))}. Is the arches-lingo package installed?"
        )
    return list(graphs_by_slug.values())


def dump_lingo_fixtures(storage_key=DEFAULT_FIXTURE_STORAGE_KEY):
    """Stream all concept/scheme (and related reference) data, plus the
    uploaded files they reference, into a single tar.gz archive, and save it
    to Django's default file storage at `storage_key`. Returns a dict of row
    counts per table plus the number of media files archived."""

    graph_ids = get_lingo_fixture_graph_ids()
    row_counts = {}

    with tempfile.NamedTemporaryFile(suffix=".tar.gz") as archive_file:
        with tarfile.open(fileobj=archive_file, mode="w:gz") as tar:
            with connection.cursor() as cursor:
                for table in FIXTURE_TABLES:
                    row_counts[table.name] = _copy_table_into_tar(
                        cursor, tar, table, graph_ids
                    )
            row_counts["media_files"] = _copy_media_files_into_tar(tar, graph_ids)

        archive_file.flush()
        archive_file.seek(0)
        if default_storage.exists(storage_key):
            default_storage.delete(storage_key)
        default_storage.save(storage_key, DjangoFile(archive_file))

    return row_counts


def load_lingo_fixtures(storage_key=DEFAULT_FIXTURE_STORAGE_KEY, index=True):
    """Restore a snapshot previously written by `dump_lingo_fixtures` from
    Django's default file storage at `storage_key`. Loads all table data in a
    single deferred-constraint transaction, restores the uploaded files, bumps
    the identity sequences those tables rely on, and (by default) reindexes
    the affected resources in Elasticsearch."""

    row_counts = {}

    with default_storage.open(storage_key, "rb") as archive_file:
        with tarfile.open(fileobj=archive_file, mode="r:gz") as tar:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SET CONSTRAINTS ALL DEFERRED")
                    for table in FIXTURE_TABLES:
                        row_counts[table.name] = _copy_table_from_tar(
                            cursor, tar, table
                        )
                    _reset_identity_sequences(cursor)
            row_counts["media_files"] = _restore_media_files_from_tar(tar)

    graph_ids = get_lingo_fixture_graph_ids()
    if index:
        call_command(
            "es",
            "index_resources_by_type",
            resource_types=[str(graph_id) for graph_id in graph_ids],
        )

    return row_counts


def _copy_table_into_tar(cursor, tar, table, graph_ids):
    column_list_sql = ", ".join(table.columns)
    copy_to_sql = cursor.mogrify(
        f"COPY (SELECT {column_list_sql} FROM {table.name} WHERE {table.where_sql}) "
        "TO STDOUT WITH (FORMAT csv, HEADER)",
        {"graph_ids": graph_ids},
    )
    with tempfile.NamedTemporaryFile() as table_csv_file:
        cursor.copy_expert(copy_to_sql, table_csv_file)
        row_count = cursor.rowcount
        table_csv_file.flush()
        tar.add(table_csv_file.name, arcname=f"db/{table.name}.csv")
    return row_count


def _copy_table_from_tar(cursor, tar, table):
    table_member = tar.getmember(f"db/{table.name}.csv")
    table_csv_file = tar.extractfile(table_member)

    # Read the column order out of the archive itself instead of assuming it
    # matches this installation's model field order: the same table can be
    # declared with a different field order in a different arches version, and
    # a mismatch would silently copy values into the wrong columns.
    header_line = table_csv_file.readline().decode("utf-8")
    archived_columns = next(csv.reader([header_line]), [])
    unrecognized_columns = set(archived_columns) - set(table.columns)
    if unrecognized_columns:
        raise ValueError(
            f"The archived {table.name} data has columns that do not exist on "
            f"this installation: {', '.join(sorted(unrecognized_columns))}. The "
            "archive was likely created against an incompatible schema version."
        )

    column_list_sql = ", ".join(archived_columns)
    copy_from_sql = (
        f"COPY {table.name} ({column_list_sql}) FROM STDIN WITH (FORMAT csv)"
    )
    cursor.copy_expert(copy_from_sql, table_csv_file)
    return cursor.rowcount


def _reset_identity_sequences(cursor):
    for table in FIXTURE_TABLES:
        if table.identity_column is None:
            continue
        cursor.execute(
            f"SELECT setval(pg_get_serial_sequence(%s, %s), "
            f"COALESCE((SELECT MAX({table.identity_column}) FROM {table.name}), 1))",
            [table.name, table.identity_column],
        )


def _copy_media_files_into_tar(tar, graph_ids):
    tile_ids_sql = (
        "SELECT tileid FROM tiles WHERE resourceinstanceid IN "
        f"({_GRAPH_FILTERED_RESOURCE_IDS_SQL})"
    )
    with connection.cursor() as cursor:
        cursor.execute(tile_ids_sql, {"graph_ids": graph_ids})
        tile_ids = [row[0] for row in cursor.fetchall()]

    archived_file_count = 0
    for file_instance in File.objects.filter(tile_id__in=tile_ids):
        field_file = file_instance.path
        if not field_file:
            continue
        field_file.open("rb")
        try:
            tar_info = tarfile.TarInfo(name=f"media/{field_file.name}")
            tar_info.size = field_file.size
            tar.addfile(tar_info, field_file)
        finally:
            field_file.close()
        archived_file_count += 1
    return archived_file_count


def _restore_media_files_from_tar(tar):
    restored_file_count = 0
    for member in tar.getmembers():
        if not member.isfile() or not member.name.startswith("media/"):
            continue
        extracted_file = tar.extractfile(member)
        if extracted_file is None:
            continue
        storage_name = member.name.removeprefix("media/")
        if default_storage.exists(storage_name):
            default_storage.delete(storage_name)
        default_storage.save(storage_name, ContentFile(extracted_file.read()))
        restored_file_count += 1
    return restored_file_count
