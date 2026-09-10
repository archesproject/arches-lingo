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


def _copy_rows(cursor, table, columns, rows):
    """Stream rows into a table with COPY, in batches, returning the count."""
    written = 0
    batch = io.StringIO()
    writer = csv.writer(batch)
    batched = 0

    def flush():
        nonlocal batch, writer, batched
        if not batched:
            return
        batch.seek(0)
        cursor.copy_expert(
            f"COPY {table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv)",
            batch,
        )
        batch = io.StringIO()
        writer = csv.writer(batch)
        batched = 0

    for row in rows:
        writer.writerow(row)
        batched += 1
        written += 1
        if batched >= COPY_BATCH_ROWS:
            flush()
    flush()
    return written


@transaction.atomic
def load_resources_and_tiles(resource_rows, tile_rows, graph_ids, log=print):
    """Write resources and tiles directly, then derive their relationships.

    `resource_rows` is an iterable of
    `(resourceinstanceid, graphid, legacyid, lifecycle_state_id)`.
    `tile_rows` is an iterable of
    `(tileid, resourceinstanceid, nodegroupid, sortorder, tiledata_dict)`.
    """
    with connection.cursor() as cursor:
        # Resources are written through a temp table so a rerun that overlaps
        # existing ids does not fail; the staging function likewise skips
        # resources that already exist.
        cursor.execute(
            """
            CREATE TEMP TABLE incoming_resource (
                resourceinstanceid uuid,
                graphid uuid,
                legacyid text,
                resource_instance_lifecycle_state_id uuid
            ) ON COMMIT DROP
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
        )
        log(f"  wrote {tile_count:,} tiles")

        # One set-based equivalent of __arches_refresh_tile_resource_relationships
        # over every tile just written, rather than a call per tile.
        cursor.execute(
            """
            WITH relationship AS (
                SELECT tile.tileid,
                       tile.resourceinstanceid AS from_id,
                       node.nodeid,
                       jsonb_array_elements(tile.tiledata -> node.nodeid::text) AS reference
                  FROM tiles tile
                  JOIN nodes node ON node.nodegroupid = tile.nodegroupid
                 WHERE node.datatype IN ('resource-instance', 'resource-instance-list')
                   AND tile.tiledata ->> node.nodeid::text IS NOT NULL
                   AND tile.resourceinstanceid IN (
                       SELECT resourceinstanceid FROM resource_instances
                        WHERE graphid = ANY(%(graph_ids)s::uuid[])
                   )
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
            """,
            {"graph_ids": list(graph_ids)},
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
