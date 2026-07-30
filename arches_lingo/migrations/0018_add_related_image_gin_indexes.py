from django.db import migrations

from arches_lingo.const import (
    DIGITAL_OBJECT_NAME_CONTENT_NODE,
    DIGITAL_OBJECT_NAME_NODEGROUP,
    DIGITAL_OBJECT_STATEMENT_CONTENT_NODE,
    DIGITAL_OBJECT_STATEMENT_NODEGROUP,
)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("arches_lingo", "0017_add_scheme_lock"),
    ]

    operations = [
        # digital object name (title)
        migrations.RunSQL(
            sql=f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    tiles_digital_object_name_trgm
                ON tiles
                USING GIN (
                    (tiledata ->> '{DIGITAL_OBJECT_NAME_CONTENT_NODE}')
                    gin_trgm_ops
                )
                WHERE nodegroupid = '{DIGITAL_OBJECT_NAME_NODEGROUP}'::uuid;
            """,
            reverse_sql="DROP INDEX IF EXISTS tiles_digital_object_name_trgm;",
        ),
        # digital object statement (description)
        migrations.RunSQL(
            sql=f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    tiles_digital_object_statement_trgm
                ON tiles
                USING GIN (
                    (tiledata ->> '{DIGITAL_OBJECT_STATEMENT_CONTENT_NODE}')
                    gin_trgm_ops
                )
                WHERE nodegroupid = '{DIGITAL_OBJECT_STATEMENT_NODEGROUP}'::uuid;
            """,
            reverse_sql="DROP INDEX IF EXISTS tiles_digital_object_statement_trgm;",
        ),
    ]
