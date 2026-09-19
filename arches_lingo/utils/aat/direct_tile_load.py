"""Write resources and tiles straight to the database, bypassing load_staging.

The Arches ETL route stages every tile, then a PL/pgSQL function walks the
staged rows one at a time to build resources, tiles, edit-log entries and
resource relationships. That loop is the dominant cost of a vocabulary import:
around three statements per staged row plus a second full pass, which for the
AAT's ~1.1M tiles measured at over two hours.

The data this loader produces is generated rather than user-entered, and every
value has already been through the datatype's own validation before it gets
here, so the staging round-trip buys little. This module writes the same rows
the staging function would have written, using COPY and set-based SQL, in the
same shape:

  * `resource_instances` rows carry the graph's initial lifecycle state
  * `tiles.tiledata` maps node id to the datatype's tile value
  * resource-instance entries get a generated `resourceXresourceId`
  * `resource_x_resource` is derived from the tiles, as
    `__arches_refresh_tile_resource_relationships` derives it

Not written: `edit_log`. A bulk vocabulary load produces one audit row per tile
duplicating the whole payload, and `lingo_fixtures` already treats edit history
as something that does not need to survive a reload.
"""

import csv
import io
import json
import uuid

from django.db import connection, transaction

COPY_BATCH_ROWS = 50_000

RESOURCE_INSTANCE_DATATYPES = frozenset(["resource-instance", "resource-instance-list"])


class TileValidationError(Exception):
    """Raised when staged values fail datatype validation before any write."""

    def __init__(self, errors):
        self.errors = errors
        sample = "; ".join(
            f"{error['nodeid']}: {error['message']}" for error in errors[:5]
        )
        super().__init__(
            f"{len(errors)} value(s) failed validation before loading. {sample}"
        )


def build_tiledata(tile_value_envelope):
    """Convert a staging envelope into the tiledata a tile row stores.

    The envelope carries per-node metadata the ETL uses; a tile keeps only the
    values. Resource-instance references are given the cross-reference id that
    `resource_x_resource` is later keyed on.
    """
    tiledata = {}
    for node_id, node_envelope in tile_value_envelope.items():
        node_value = node_envelope.get("value")
        if node_envelope.get("datatype") in RESOURCE_INSTANCE_DATATYPES and node_value:
            node_value = [
                {**reference, "resourceXresourceId": str(uuid.uuid4())}
                for reference in node_value
            ]
        tiledata[node_id] = node_value
    return tiledata


class _CopyBuffer:
    """Accumulate CSV rows for one table and hand them to COPY in batches."""

    def __init__(self, cursor, table, columns):
        self.cursor = cursor
        self.copy_statement = (
            f"COPY {table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv)"
        )
        self._start_batch()

    def _start_batch(self):
        self.batch = io.StringIO()
        self.writer = csv.writer(self.batch)
        self.batched_row_count = 0

    def add(self, row):
        self.writer.writerow(row)
        self.batched_row_count += 1

    def flush(self):
        if not self.batched_row_count:
            return
        self.batch.seek(0)
        self.cursor.copy_expert(self.copy_statement, self.batch)
        self._start_batch()


def _copy_rows(cursor, table, columns, rows, mirror=None):
    """Stream rows into a table with COPY, in batches, returning the count.

    `mirror` is an optional `(table, columns, project)` triple. Each row is
    also written to that table as `project(row)`, flushed alongside the rows
    themselves so neither buffer grows past `COPY_BATCH_ROWS`.
    """
    written = 0
    primary_buffer = _CopyBuffer(cursor, table, columns)
    mirror_buffer = None
    project_mirrored_row = None
    if mirror:
        mirror_table, mirror_columns, project_mirrored_row = mirror
        mirror_buffer = _CopyBuffer(cursor, mirror_table, mirror_columns)

    for row in rows:
        primary_buffer.add(row)
        if mirror_buffer is not None:
            mirror_buffer.add(project_mirrored_row(row))
        written += 1
        if written % COPY_BATCH_ROWS == 0:
            primary_buffer.flush()
            if mirror_buffer is not None:
                mirror_buffer.flush()

    primary_buffer.flush()
    if mirror_buffer is not None:
        mirror_buffer.flush()
    return written


@transaction.atomic
def load_resources_and_tiles(resource_rows, tile_rows, log=print):
    """Write resources and tiles directly, then derive their relationships.

    `resource_rows` is an iterable of
    `(resourceinstanceid, graphid, legacyid, lifecycle_state_id)`.
    `tile_rows` is an iterable of
    `(tileid, resourceinstanceid, nodegroupid, sortorder, tiledata_dict)`.
    """
    with connection.cursor() as cursor:
        # Resources are written through a temp table so a rerun that overlaps
        # existing ids does not fail; the staging function likewise skips
        # resources that already exist. Tile ids are collected in a second temp
        # table so the relationship pass below sees only the tiles this load
        # wrote. ON COMMIT DROP only fires on a real commit, so a caller holding
        # an outer transaction would otherwise find the tables still there on a
        # second call.
        cursor.execute(
            """
            DROP TABLE IF EXISTS incoming_resource;
            CREATE TEMP TABLE incoming_resource (
                resourceinstanceid uuid,
                graphid uuid,
                legacyid text,
                resource_instance_lifecycle_state_id uuid
            ) ON COMMIT DROP;
            DROP TABLE IF EXISTS incoming_tile;
            CREATE TEMP TABLE incoming_tile (tileid uuid) ON COMMIT DROP
            """
        )
        resource_count = _copy_rows(
            cursor,
            "incoming_resource",
            (
                "resourceinstanceid",
                "graphid",
                "legacyid",
                "resource_instance_lifecycle_state_id",
            ),
            resource_rows,
        )
        cursor.execute(
            """
            INSERT INTO resource_instances (
                resourceinstanceid, graphid, legacyid, createdtime,
                resource_instance_lifecycle_state_id
            )
            SELECT resourceinstanceid, graphid, legacyid, now(),
                   resource_instance_lifecycle_state_id
              FROM incoming_resource
            ON CONFLICT (resourceinstanceid) DO NOTHING
            """
        )
        log(f"  wrote {resource_count:,} resources")

        tile_count = _copy_rows(
            cursor,
            "tiles",
            ("tileid", "resourceinstanceid", "nodegroupid", "sortorder", "tiledata"),
            tile_rows,
            mirror=("incoming_tile", ("tileid",), lambda tile_row: (tile_row[0],)),
        )
        cursor.execute("CREATE INDEX ON incoming_tile (tileid)")
        cursor.execute("ANALYZE incoming_tile")
        log(f"  wrote {tile_count:,} tiles")

        # One set-based equivalent of __arches_refresh_tile_resource_relationships
        # over the tiles just written, rather than a call per tile. Tiles that
        # were already in the graph keep the relationship rows they already
        # have; re-deriving them would collide on resource_x_resource's key.
        cursor.execute(
            """
            WITH relationship AS (
                SELECT tile.tileid,
                       tile.resourceinstanceid AS from_id,
                       node.nodeid,
                       jsonb_array_elements(tile.tiledata -> node.nodeid::text) AS reference
                  FROM tiles tile
                  JOIN incoming_tile incoming ON incoming.tileid = tile.tileid
                  JOIN nodes node ON node.nodegroupid = tile.nodegroupid
                 WHERE node.datatype IN ('resource-instance', 'resource-instance-list')
                   AND jsonb_typeof(tile.tiledata -> node.nodeid::text) = 'array'
            )
            INSERT INTO resource_x_resource (
                resourcexid, notes, relationshiptype, resourceinstanceidfrom,
                resourceinstanceidto, inverserelationshiptype, tileid, nodeid,
                created, modified, resourceinstancefrom_graphid,
                resourceinstanceto_graphid
            )
            SELECT CASE reference ->> 'resourceXresourceId'
                       WHEN '' THEN uuid_generate_v4()
                       ELSE (reference ->> 'resourceXresourceId')::uuid
                   END,
                   '',
                   reference ->> 'ontologyProperty',
                   relationship.from_id,
                   (reference ->> 'resourceId')::uuid,
                   reference ->> 'inverseOntologyProperty',
                   relationship.tileid,
                   relationship.nodeid,
                   now(), now(),
                   resource_from.graphid,
                   resource_to.graphid
              FROM relationship
              LEFT JOIN resource_instances resource_from
                     ON resource_from.resourceinstanceid = relationship.from_id
              LEFT JOIN resource_instances resource_to
                     ON resource_to.resourceinstanceid
                        = (reference ->> 'resourceId')::uuid
             WHERE reference ->> 'resourceId' IS NOT NULL
            """
        )
        log(f"  wrote {cursor.rowcount:,} resource relationships")

    return {"resources": resource_count, "tiles": tile_count}


def tiledata_for_copy(tiledata):
    """Render tiledata as the JSON text COPY expects."""
    return json.dumps(tiledata)


@transaction.atomic
def merge_into_tiledata(tile_additions, log=print):
    """Add nodes to existing tiles without rewriting the tiles themselves.

    Attribution only adds two resource-instance nodes to a label or note tile.
    Routing that through staging means resending every untouched node on the
    tile so the staging function can replace `tiledata` wholesale; merging the
    new keys in place sends only what changes.

    `tile_additions` is an iterable of `(tileid, {node_id: value})`. Resource
    references are given the cross-reference id `resource_x_resource` is keyed
    on, and the matching relationship rows are written here too, since the
    staging function is no longer doing it.
    """
    # Several entries can resolve to the same tile -- two labels sharing a
    # literal form and language, for instance -- so additions are combined per
    # tile rather than sent as competing rows.
    additions_by_tile = {}
    for tile_id, node_values in tile_additions:
        addition = additions_by_tile.setdefault(str(tile_id), {})
        for node_id, node_value in node_values.items():
            if isinstance(node_value, list):
                node_value = [
                    {**reference, "resourceXresourceId": str(uuid.uuid4())}
                    for reference in node_value
                ]
            addition[node_id] = node_value

    prepared_rows = [
        (tile_id, json.dumps(addition))
        for tile_id, addition in additions_by_tile.items()
    ]

    if not prepared_rows:
        return 0

    with connection.cursor() as cursor:
        cursor.execute(
            """
            DROP TABLE IF EXISTS incoming_tile_addition;
            CREATE TEMP TABLE incoming_tile_addition (
                tileid uuid PRIMARY KEY,
                addition jsonb
            ) ON COMMIT DROP
            """
        )
        _copy_rows(
            cursor, "incoming_tile_addition", ("tileid", "addition"), prepared_rows
        )
        cursor.execute("ANALYZE incoming_tile_addition")

        cursor.execute(
            """
            UPDATE tiles
               SET tiledata = tiles.tiledata || incoming.addition
              FROM incoming_tile_addition incoming
             WHERE tiles.tileid = incoming.tileid
            """
        )
        merged_count = cursor.rowcount
        log(f"  merged attribution into {merged_count:,} tiles")

        # Rebuild relationships for exactly the tiles just touched.
        cursor.execute(
            """
            DELETE FROM resource_x_resource
             WHERE tileid IN (SELECT tileid FROM incoming_tile_addition)
            """
        )
        cursor.execute(
            """
            WITH relationship AS (
                SELECT tile.tileid,
                       tile.resourceinstanceid AS from_id,
                       node.nodeid,
                       jsonb_array_elements(tile.tiledata -> node.nodeid::text)
                           AS reference
                  FROM tiles tile
                  JOIN incoming_tile_addition incoming
                    ON incoming.tileid = tile.tileid
                  JOIN nodes node ON node.nodegroupid = tile.nodegroupid
                 WHERE node.datatype IN ('resource-instance', 'resource-instance-list')
                   AND jsonb_typeof(tile.tiledata -> node.nodeid::text) = 'array'
            )
            INSERT INTO resource_x_resource (
                resourcexid, notes, relationshiptype, resourceinstanceidfrom,
                resourceinstanceidto, inverserelationshiptype, tileid, nodeid,
                created, modified, resourceinstancefrom_graphid,
                resourceinstanceto_graphid
            )
            SELECT CASE reference ->> 'resourceXresourceId'
                       WHEN '' THEN uuid_generate_v4()
                       ELSE (reference ->> 'resourceXresourceId')::uuid
                   END,
                   '',
                   reference ->> 'ontologyProperty',
                   relationship.from_id,
                   (reference ->> 'resourceId')::uuid,
                   reference ->> 'inverseOntologyProperty',
                   relationship.tileid,
                   relationship.nodeid,
                   now(), now(),
                   resource_from.graphid,
                   resource_to.graphid
              FROM relationship
              LEFT JOIN resource_instances resource_from
                     ON resource_from.resourceinstanceid = relationship.from_id
              LEFT JOIN resource_instances resource_to
                     ON resource_to.resourceinstanceid
                        = (reference ->> 'resourceId')::uuid
             WHERE reference ->> 'resourceId' IS NOT NULL
            """
        )
        log(f"  wrote {cursor.rowcount:,} attribution relationships")

    return merged_count
