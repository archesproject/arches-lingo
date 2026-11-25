from django.db import migrations

from arches_lingo.const import CONCEPT_NAME_CONTENT_NODE, CONCEPT_NAME_NODEGROUP


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("arches_lingo", "0021_add_uri_and_part_of_scheme_indexes"),
    ]

    # unaccent() is only STABLE, because its dictionary can change, so it cannot
    # appear in an index. Naming the dictionary explicitly in an IMMUTABLE
    # wrapper is the standard way to index unaccented text.
    operations = [
        migrations.RunSQL(
            sql="""
                CREATE EXTENSION IF NOT EXISTS unaccent;
                CREATE OR REPLACE FUNCTION __arches_lingo_immutable_unaccent(text)
                    RETURNS text
                    LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
                AS $$
                    SELECT public.unaccent('public.unaccent'::regdictionary, $1)
                $$;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS __arches_lingo_immutable_unaccent(text);",
        ),
        migrations.RunSQL(
            sql=f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    tiles_unaccented_label_content_trgm
                ON tiles
                USING GIN (
                    __arches_lingo_immutable_unaccent(
                        tiledata ->> '{CONCEPT_NAME_CONTENT_NODE}'
                    )
                    gin_trgm_ops
                )
                WHERE nodegroupid = '{CONCEPT_NAME_NODEGROUP}';
            """,
            reverse_sql="DROP INDEX IF EXISTS tiles_unaccented_label_content_trgm;",
        ),
    ]
