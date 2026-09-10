"""Save an ETL load without writing to Elasticsearch.

Arches' bulk loader always indexes at the end of a load, and indexing is the
slowest part of importing a large vocabulary. Many Lingo deployments do not
query Elasticsearch at all, so this offers the same save without it.

Descriptors are still recalculated. They are what the interface displays as a
resource's name, they live in the database rather than the index, and arches
only refreshes them as a side effect of indexing -- so skipping indexing
outright would leave every imported resource showing a stale or empty name.
"""

from django.contrib.auth.models import User
from django.db import connection

from arches.app.etl_modules.save import (
    _save_to_tiles,
    disable_tile_triggers,
    log_event_details,
    reenable_tile_triggers,
)
from arches.app.models.resource import Resource
from arches.app.utils.index_database import optimize_resource_iteration


def _recalculate_descriptors_for_transaction(cursor, loadid):
    cursor.execute(
        "SELECT DISTINCT resourceinstanceid FROM edit_log WHERE transactionid = %s",
        [loadid],
    )
    resource_ids = [resource_id for (resource_id,) in cursor.fetchall()]

    # descriptor_function is not a field on the graph: optimize_resource_iteration
    # prefetches it there, and the caller moves it onto the resource.
    for resource in optimize_resource_iteration(
        Resource.objects.filter(pk__in=resource_ids), chunk_size=2000
    ):
        resource.tiles = resource.prefetched_tiles
        resource.descriptor_function = resource.graph.descriptor_function
        resource.save_descriptors()

    return len(resource_ids)


def _attribute_edit_log_to_user(cursor, userid, loadid):
    user = User.objects.get(id=userid)
    cursor.execute(
        """
            UPDATE edit_log edit
               SET (resourcedisplayname, userid, user_firstname, user_lastname,
                    user_email, user_username)
                 = (resource.name ->> %s, %s, %s, %s, %s, %s)
              FROM resource_instances resource
             WHERE edit.resourceinstanceid::uuid = resource.resourceinstanceid
               AND edit.transactionid = %s
        """,
        [
            "en",
            userid,
            getattr(user, "first_name", ""),
            getattr(user, "last_name", ""),
            getattr(user, "email", ""),
            getattr(user, "username", ""),
            loadid,
        ],
    )


def save_to_tiles_without_indexing(userid, loadid):
    """Write staged tiles and refresh descriptors, leaving the index alone.

    Mirrors arches.app.etl_modules.save.save_to_tiles, minus the call to
    index_resources_by_transaction.
    """
    with connection.cursor() as cursor:
        disable_tile_triggers(cursor, loadid)
        error_saving_tiles = _save_to_tiles(cursor, loadid)
        reenable_tile_triggers(cursor, loadid)
        if error_saving_tiles:
            return error_saving_tiles

        log_event_details(cursor, loadid, "done|Recalculating descriptors...")
        _recalculate_descriptors_for_transaction(cursor, loadid)

        log_event_details(cursor, loadid, "done|Updating the edit log...")
        _attribute_edit_log_to_user(cursor, userid, loadid)

        cursor.execute(
            "UPDATE load_event SET status = %s, indexed_time = now(), "
            "complete = true, successful = true WHERE loadid = %s",
            ("indexed", loadid),
        )
    return {"success": True, "data": "indexing complete"}
