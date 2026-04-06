from django.db import migrations

from arches_lingo.const import (
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    CLASSIFICATION_STATUS_NODEGROUP,
)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("arches_lingo", "0012_add_label_search_index"),
    ]

    operations = [
        migrations.RunSQL(
            sql=f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    tiles_broader_concept_gin
                ON tiles
                USING GIN (
                    (tiledata -> '{CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID}')
                    jsonb_path_ops
                )
                WHERE nodegroupid = '{CLASSIFICATION_STATUS_NODEGROUP}'::uuid;
            """,
            reverse_sql="DROP INDEX IF EXISTS tiles_broader_concept_gin;",
        ),
    ]
