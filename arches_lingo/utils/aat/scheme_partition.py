"""Read and remove the resources belonging to a single scheme.

Reloading a vocabulary means replacing the resources it previously produced.
Concepts alone are not enough: the load also creates the textual_work and group
resources that carry source and contributor attribution, and those are reachable
only from the concepts that cite them.
"""

from django.db import connection, transaction

from arches_lingo import const

ATTRIBUTION_GRAPH_NAMES = (
    "Textual Work (system)",
    "Group (system)",
    "Person (system)",
)

DELETABLE_GRAPH_NAMES = ("Concept",) + ATTRIBUTION_GRAPH_NAMES

_CONCEPTS_IN_SCHEME_SQL = f"""
    SELECT resourceinstanceid
    FROM tiles
    WHERE nodegroupid = '{const.CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}'
      AND tiledata -> '{const.CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}' -> 0 ->> 'resourceId'
          = %(scheme_id)s
"""

# Attribution resources cited only by concepts in this scheme. bool_and over the
# citing concepts means a source shared with another vocabulary is never caught.
_SCHEME_ONLY_ATTRIBUTION_SQL = f"""
    SELECT candidate.target_id
    FROM (
        SELECT relation.resourceinstanceidto AS target_id,
               bool_and(
                   relation.resourceinstanceidfrom IN ({_CONCEPTS_IN_SCHEME_SQL})
               ) AS cited_only_by_scheme
        FROM resource_x_resource relation
        WHERE relation.resourceinstanceidto NOT IN ({_CONCEPTS_IN_SCHEME_SQL})
          AND relation.resourceinstanceidto <> %(scheme_id)s::uuid
        GROUP BY relation.resourceinstanceidto
    ) candidate
    JOIN resource_instances resource
      ON resource.resourceinstanceid = candidate.target_id
    JOIN graphs graph ON graph.graphid = resource.graphid
    WHERE candidate.cited_only_by_scheme
      AND graph.name ->> 'en' = ANY(%(attribution_graph_names)s)
"""


def summarize_scheme_partition(scheme_resource_instance_id):
    """Return {model name: resource count} for everything purge would remove."""
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT graph.name ->> 'en' AS model_name, count(*)
            FROM (
                SELECT resourceinstanceid AS id FROM ({_CONCEPTS_IN_SCHEME_SQL}) concepts
                UNION
                SELECT target_id AS id FROM ({_SCHEME_ONLY_ATTRIBUTION_SQL}) attribution
            ) doomed
            JOIN resource_instances resource ON resource.resourceinstanceid = doomed.id
            JOIN graphs graph ON graph.graphid = resource.graphid
            GROUP BY 1 ORDER BY 2 DESC
            """,
            {
                "scheme_id": str(scheme_resource_instance_id),
                "attribution_graph_names": list(ATTRIBUTION_GRAPH_NAMES),
            },
        )
        return {model_name: count for model_name, count in cursor.fetchall()}


@transaction.atomic
def purge_scheme_partition(scheme_resource_instance_id, log=print):
    """Delete a scheme's concepts and the attribution resources only they cite.

    The scheme resource itself is kept so records that hold a foreign key to it
    (its URI template and attribution statement) survive; its tiles are cleared
    so a reload recreates them instead of duplicating them.

    Raises RuntimeError rather than deleting anything if the computed scope
    reaches a resource model it should never touch.
    """
    scheme_id = str(scheme_resource_instance_id)
    query_parameters = {
        "scheme_id": scheme_id,
        "attribution_graph_names": list(ATTRIBUTION_GRAPH_NAMES),
    }

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            CREATE TEMP TABLE doomed_resource ON COMMIT DROP AS
            SELECT resourceinstanceid AS id FROM ({_CONCEPTS_IN_SCHEME_SQL}) concepts
            UNION
            SELECT target_id AS id FROM ({_SCHEME_ONLY_ATTRIBUTION_SQL}) attribution
            """,
            query_parameters,
        )
        cursor.execute("CREATE INDEX ON doomed_resource (id)")

        cursor.execute(
            """
            SELECT count(*)
            FROM doomed_resource
            JOIN resource_instances resource
              ON resource.resourceinstanceid = doomed_resource.id
            JOIN graphs graph ON graph.graphid = resource.graphid
            WHERE graph.name ->> 'en' <> ALL(%(deletable_graph_names)s)
            """,
            {"deletable_graph_names": list(DELETABLE_GRAPH_NAMES)},
        )
        unexpected_model_count = cursor.fetchone()[0]
        if unexpected_model_count:
            raise RuntimeError(
                f"Refusing to purge: {unexpected_model_count} resources of an "
                f"unexpected model are in scope for scheme {scheme_id}"
            )

        cursor.execute(
            """
            DELETE FROM resource_x_resource
             WHERE resourceinstanceidfrom IN (SELECT id FROM doomed_resource)
                OR resourceinstanceidto IN (SELECT id FROM doomed_resource)
                OR resourceinstanceidfrom = %(scheme_id)s::uuid
                OR resourceinstanceidto = %(scheme_id)s::uuid
            """,
            {"scheme_id": scheme_id},
        )
        cursor.execute(
            "DELETE FROM tiles WHERE resourceinstanceid = %(scheme_id)s::uuid",
            {"scheme_id": scheme_id},
        )
        cursor.execute(
            "DELETE FROM tiles WHERE resourceinstanceid IN (SELECT id FROM doomed_resource)"
        )
        cursor.execute(
            "DELETE FROM resource_identifiers WHERE resourceid_id IN (SELECT id FROM doomed_resource)"
        )
        cursor.execute(
            "DELETE FROM resource_instances WHERE resourceinstanceid IN (SELECT id FROM doomed_resource)"
        )
        deleted_resource_count = cursor.rowcount

    log(f"Purged {deleted_resource_count:,} resources from scheme {scheme_id}")
    return deleted_resource_count
