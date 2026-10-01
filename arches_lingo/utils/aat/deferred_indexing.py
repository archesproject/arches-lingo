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

from arches_lingo.utils.aat.progress import (
    iterate_with_progress,
    progress_reporting_is_useful,
)

__all__ = [
    "recalculate_descriptors_for_resources",
    "save_to_tiles_without_indexing",
]

DESCRIPTOR_BATCH_SIZE = 1000


def recalculate_descriptors_for_resources(resource_ids, log=print):
    """Recompute descriptors for the given resources.

    Used by loads that write tiles directly: descriptors are what the interface
    shows as a resource's name, and nothing else recalculates them once the
    Arches save path is not involved.
    """
    log(f"  recalculating descriptors for {len(resource_ids):,} resources ...")
    _recalculate_descriptors(resource_ids, show_progress=progress_reporting_is_useful())
    return len(resource_ids)


def _recalculate_descriptors_for_transaction(cursor, loadid):
    cursor.execute(
        "SELECT DISTINCT resourceinstanceid FROM edit_log WHERE transactionid = %s",
        [loadid],
    )
    resource_ids = [resource_id for (resource_id,) in cursor.fetchall()]
    _recalculate_descriptors(resource_ids)
    return len(resource_ids)


def _recalculate_descriptors(resource_ids, show_progress=False):
    # ResourceInstance.save() reads self.graph.publication, which is a query per
    # resource unless it comes along with the graph.
    resources_to_index = Resource.objects.filter(pk__in=resource_ids).select_related(
        "graph__publication"
    )

    for resource in iterate_with_progress(
        optimize_resource_iteration(
            resources_to_index, chunk_size=DESCRIPTOR_BATCH_SIZE
        ),
        total=len(resource_ids),
        title="Recalculating descriptors",
        show_progress=show_progress,
    ):
        resource.tiles = resource.prefetched_tiles
        # descriptor_function is not a field on the graph; optimize_resource_iteration
        # prefetches it there and the caller moves it onto the resource.
        resource.descriptor_function = resource.graph.descriptor_function
        # save_descriptors() writes the row itself; there is no hook to compute
        # without saving, so this stays one UPDATE per resource.
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


def save_to_tiles_without_indexing(userid, loadid, recalculate_descriptors=True):
    """Write staged tiles and refresh descriptors, leaving the index alone.

    Mirrors arches.app.etl_modules.save.save_to_tiles, minus the call to
    index_resources_by_transaction.

    `recalculate_descriptors` may be turned off when the load cannot have
    changed any value a descriptor is built from. Recomputing is expensive --
    several queries and a row update per resource -- so skipping it when the
    result is guaranteed identical is worth the explicit argument.
    """
    with connection.cursor() as cursor:
        disable_tile_triggers(cursor, loadid)
        error_saving_tiles = _save_to_tiles(cursor, loadid)
        reenable_tile_triggers(cursor, loadid)
        if error_saving_tiles:
            return error_saving_tiles

        if recalculate_descriptors:
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
