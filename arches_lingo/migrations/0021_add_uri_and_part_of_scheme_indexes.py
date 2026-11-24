from django.db import migrations

from arches_lingo.const import (
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("arches_lingo", "0020_add_concept_match_detection"),
    ]

    # Index names and definitions match those created manually by
    # .runtime/hooks/post_load.sh so IF NOT EXISTS skips deployments that
    # already have them.
    operations = [
        migrations.RunSQL(
            sql=f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    tiles_uri_content_btree
                ON tiles ((tiledata -> '{URI_CONTENT_NODE}'))
                WHERE nodegroupid = '{URI_NODEGROUP}'::uuid;
            """,
            reverse_sql="DROP INDEX IF EXISTS tiles_uri_content_btree;",
        ),
        migrations.RunSQL(
            sql=f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    tiles_part_of_scheme_covering
                ON tiles (resourceinstanceid)
                INCLUDE (tiledata, parenttileid, sortorder)
                WHERE nodegroupid = '{CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}'::uuid;
            """,
            reverse_sql="DROP INDEX IF EXISTS tiles_part_of_scheme_covering;",
        ),
        migrations.RunSQL(
            sql=f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    tiles_part_of_scheme_gin
                ON tiles
                USING GIN (
                    (tiledata -> '{CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}')
                    jsonb_path_ops
                )
                WHERE nodegroupid = '{CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}'::uuid;
            """,
            reverse_sql="DROP INDEX IF EXISTS tiles_part_of_scheme_gin;",
        ),
        migrations.RunSQL(
            sql="ANALYZE tiles;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
