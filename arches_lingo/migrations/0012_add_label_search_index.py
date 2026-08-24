from django.db import migrations

from arches_lingo.const import CONCEPT_NAME_CONTENT_NODE, CONCEPT_NAME_NODEGROUP


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("arches_lingo", "0011_add_scheme_url_template"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="DROP EXTENSION IF EXISTS pg_trgm;",
        ),
        migrations.RunSQL(
            sql=f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    tiles_label_content_trgm
                ON tiles
                USING GIN (
                    (tiledata ->> '{CONCEPT_NAME_CONTENT_NODE}')
                    gin_trgm_ops
                )
                WHERE nodegroupid = '{CONCEPT_NAME_NODEGROUP}';
            """,
            reverse_sql="DROP INDEX IF EXISTS tiles_label_content_trgm;",
        ),
    ]
