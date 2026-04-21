from django.db import migrations

from arches_lingo.const import CONCEPT_NAME_LANGUAGE_NODE, CONCEPT_NAME_NODEGROUP


class Migration(migrations.Migration):
    """Add a B-tree expression index on the language field of label tiles.

    The dashboard stats and scheme label-count views both GROUP BY the language
    value extracted from tiledata for appellative_status (label) tiles.  Without
    an index PostgreSQL must extract the language string from every matching tile
    row before hashing, which becomes expensive as concept counts grow.

    A partial B-tree index on (tiledata ->> language_node) scoped to the label
    nodegroup lets the planner avoid per-row JSONB extraction during aggregation
    and supports equality lookups used by the advanced-search language facet.
    """

    atomic = False

    dependencies = [
        ("arches_lingo", "0014_add_attribution_gin_indexes"),
    ]

    operations = [
        migrations.RunSQL(
            sql=f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    tiles_label_language_btree
                ON tiles
                    ((tiledata ->> '{CONCEPT_NAME_LANGUAGE_NODE}'))
                WHERE nodegroupid = '{CONCEPT_NAME_NODEGROUP}';
            """,
            reverse_sql="DROP INDEX IF EXISTS tiles_label_language_btree;",
        ),
    ]
