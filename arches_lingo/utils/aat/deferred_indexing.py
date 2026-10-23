"""Control when a load writes to Elasticsearch.

Arches' bulk loader always indexes at the end of a load, and indexing is the
slowest part of importing a large vocabulary. Many Lingo deployments do not
query Elasticsearch at all, so this offers the same save without it, and lets
a load that writes tiles directly index exactly the resources it wrote.

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
from arches.app.search.elasticsearch_dsl_builder import Bool, Query, Terms
from arches.app.search.mappings import RESOURCES_INDEX, TERMS_INDEX
from arches.app.search.search_engine_factory import SearchEngineInstance
from arches.app.utils.index_database import (
    index_resources_using_singleprocessing,
    optimize_resource_iteration,
)

from arches_lingo.utils.aat.progress import (
    iterate_with_progress,
    progress_reporting_is_useful,
)

__all__ = [
    "index_resources",
    "recalculate_descriptors_for_resources",
    "remove_resources_from_index",
    "save_to_tiles_without_indexing",
]

DESCRIPTOR_BATCH_SIZE = 1000
INDEX_REMOVAL_BATCH_SIZE = 1000


def recalculate_descriptors_for_resources(resource_ids, log=print):
    """Recompute descriptors for the given resources.

    Used by loads that write tiles directly: descriptors are what the interface
    shows as a resource's name, and nothing else recalculates them once the
    Arches save path is not involved.
    """
    log(f"  recalculating descriptors for {len(resource_ids):,} resources ...")
    _recalculate_descriptors(resource_ids, show_progress=progress_reporting_is_useful())
    return len(resource_ids)


def index_resources(resource_ids, recalculate_descriptors=False, log=print):
    """Write the given resources to Elasticsearch.

    `recalculate_descriptors` refreshes descriptors in the same pass, which is
    cheaper than recalculating them and then indexing separately.
    """
    log(f"  indexing {len(resource_ids):,} resources ...")
    index_resources_using_singleprocessing(
        Resource.objects.filter(pk__in=resource_ids),
        quiet=not progress_reporting_is_useful(),
        title="Indexing",
        recalculate_descriptors=recalculate_descriptors,
    )
    return len(resource_ids)


def remove_resources_from_index(resource_ids, log=print):
    """Delete the resource and term documents of resources no longer in the db.

    A purge removes rows with SQL, which leaves their documents behind, so a
    reloaded vocabulary would otherwise keep returning retired concepts.
    """
    resource_ids = [str(resource_id) for resource_id in resource_ids]
    for batch_start in range(0, len(resource_ids), INDEX_REMOVAL_BATCH_SIZE):
        batch = resource_ids[batch_start : batch_start + INDEX_REMOVAL_BATCH_SIZE]
        for index_name in (TERMS_INDEX, RESOURCES_INDEX):
            query = Query(SearchEngineInstance)
            bool_query = Bool()
            bool_query.filter(Terms(field="resourceinstanceid", terms=batch))
            query.add_query(bool_query)
            query.delete(index=index_name)
    if resource_ids:
        log(f"  removed {len(resource_ids):,} purged resources from the index")
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
