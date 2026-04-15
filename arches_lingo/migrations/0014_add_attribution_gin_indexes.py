from django.db import migrations

from arches_lingo.const import (
    CONCEPT_NAME_DATA_ASSIGNMENT_ACTOR_NODE,
    CONCEPT_NAME_DATA_ASSIGNMENT_OBJ_USED_NODE,
    CONCEPT_NAME_NODEGROUP,
    STATEMENT_DATA_ASSIGNMENT_ACTOR_NODE,
    STATEMENT_DATA_ASSIGNMENT_OBJ_USED_NODE,
    STATEMENT_NODEGROUP,
)


class Migration(migrations.Migration):
    """Add GIN expression indexes for attribution node paths.

    The attribution_source and attribution_contributor advanced search facets
    filter tiles using JSONB @> containment on two nodes (object_used / actor)
    across two nodegroups (appellative_status / statement).  Without indexes
    these queries require a full scan of every tile in each nodegroup.

    Each index is a partial, jsonb_path_ops GIN index on the extracted JSONB
    sub-tree for one node, filtered to the relevant nodegroup.  This reduces
    specific-resource-id containment lookups from O(N) to O(log N) and
    allows PostgreSQL to satisfy the compound (nodegroup + @>) predicate
    without touching tiles from other nodegroups.
    """

    atomic = False

    dependencies = [
        ("arches_lingo", "0013_add_broader_concept_gin_index"),
    ]

    operations = [
        # appellative_status (label) — source (object_used)
        migrations.RunSQL(
            sql=f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    tiles_label_obj_used_gin
                ON tiles
                USING GIN (
                    (tiledata -> '{CONCEPT_NAME_DATA_ASSIGNMENT_OBJ_USED_NODE}')
                    jsonb_path_ops
                )
                WHERE nodegroupid = '{CONCEPT_NAME_NODEGROUP}'::uuid;
            """,
            reverse_sql="DROP INDEX IF EXISTS tiles_label_obj_used_gin;",
        ),
        # appellative_status (label) — contributor (actor)
        migrations.RunSQL(
            sql=f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    tiles_label_actor_gin
                ON tiles
                USING GIN (
                    (tiledata -> '{CONCEPT_NAME_DATA_ASSIGNMENT_ACTOR_NODE}')
                    jsonb_path_ops
                )
                WHERE nodegroupid = '{CONCEPT_NAME_NODEGROUP}'::uuid;
            """,
            reverse_sql="DROP INDEX IF EXISTS tiles_label_actor_gin;",
        ),
        # statement (note) — source (object_used)
        migrations.RunSQL(
            sql=f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    tiles_statement_obj_used_gin
                ON tiles
                USING GIN (
                    (tiledata -> '{STATEMENT_DATA_ASSIGNMENT_OBJ_USED_NODE}')
                    jsonb_path_ops
                )
                WHERE nodegroupid = '{STATEMENT_NODEGROUP}'::uuid;
            """,
            reverse_sql="DROP INDEX IF EXISTS tiles_statement_obj_used_gin;",
        ),
        # statement (note) — contributor (actor)
        migrations.RunSQL(
            sql=f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    tiles_statement_actor_gin
                ON tiles
                USING GIN (
                    (tiledata -> '{STATEMENT_DATA_ASSIGNMENT_ACTOR_NODE}')
                    jsonb_path_ops
                )
                WHERE nodegroupid = '{STATEMENT_NODEGROUP}'::uuid;
            """,
            reverse_sql="DROP INDEX IF EXISTS tiles_statement_actor_gin;",
        ),
    ]
