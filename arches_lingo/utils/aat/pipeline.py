"""Run the Getty AAT load end to end.

The load is a sequence of steps that must happen in order: the SKOS conversion
produces the file the language step scans and the importer reads, and attribution
cannot be attached until the concepts it refers to exist. Each step is exposed
separately so a caller can resume after a failure without repeating the slow
download and conversion.
"""

import os
import tempfile

from django.core.management import call_command
from django.db import connection

from arches.app.models.models import ResourceInstance

from arches_lingo import const
from arches_lingo.utils.aat.attribution_extraction import (
    extract_attribution_from_archive,
)
from arches_lingo.utils.aat.attribution_statement import (
    build_aat_attribution,
    set_scheme_attribution,
)
from arches_lingo.utils.aat.languages import (
    ensure_languages,
    repair_colliding_language_names,
)
from arches_lingo.utils.aat.resource_id_pinning import write_resource_id_snapshot
from arches_lingo.utils.aat.scheme_partition import (
    purge_scheme_partition,
    summarize_scheme_partition,
)
from arches_lingo.utils.concept_lifecycle import LOCKED_STATE_ID
from arches_lingo.utils.aat.skos_conversion import (
    DEFAULT_SCHEME_IDENTIFIER_URI,
    DEFAULT_SCHEME_PREF_LABEL,
    GETTY_AAT_EXPLICIT_ZIP_URL,
    convert_archive_to_skos,
    download_archive,
    read_archive_extraction_date,
)

AAT_URI_PREFIX = "http://vocab.getty.edu/aat/"

# The converted AAT export is larger than the importer's default threshold for
# handing work to a celery worker. Raising it for this import only keeps the
# load in-process, so no worker is required and the pinned-id map is not lost
# crossing a process boundary.
AAT_CELERY_BYTE_SIZE_LIMIT = 2_000_000_000

SKOS_FILENAME = "getty_aat_skos.xml"
ATTRIBUTION_FILENAME = "getty_aat_attribution.json"
RESOURCE_ID_SNAPSHOT_FILENAME = "getty_aat_resource_ids.csv"


def remove_orphaned_aat_schemes(keep_scheme_id, log=print):
    """Delete AAT scheme resources that hold no tiles and no concepts.

    A scheme that was created by a load which then failed, or by an earlier
    version that did not pin the scheme id, is left behind with nothing
    attached to it. Without this the vocabulary appears more than once.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT scheme.resourceinstanceid
              FROM resource_instances scheme
             WHERE scheme.graphid = %(schemes_graph_id)s::uuid
               AND scheme.resourceinstanceid <> %(keep_scheme_id)s::uuid
               AND NOT EXISTS (
                   SELECT 1 FROM tiles WHERE resourceinstanceid = scheme.resourceinstanceid
               )
               AND NOT EXISTS (
                   SELECT 1 FROM tiles part_of_scheme
                    WHERE part_of_scheme.nodegroupid
                          = '{const.CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}'
                      AND (part_of_scheme.tiledata
                           -> '{const.CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}'
                           -> 0 ->> 'resourceId')::uuid
                          = scheme.resourceinstanceid
               )
            """,
            {
                "schemes_graph_id": const.SCHEMES_GRAPH_ID,
                "keep_scheme_id": str(keep_scheme_id),
            },
        )
        orphaned_scheme_ids = [scheme_id for (scheme_id,) in cursor.fetchall()]

        for scheme_id in orphaned_scheme_ids:
            # Records keyed to the scheme hold a foreign key to it.
            cursor.execute(
                "DELETE FROM concept_identifier_counters "
                "WHERE scheme_resource_instance_id = %s",
                [scheme_id],
            )
            cursor.execute(
                "DELETE FROM scheme_uri_templates "
                "WHERE scheme_resource_instance_id = %s",
                [scheme_id],
            )
            cursor.execute(
                "DELETE FROM scheme_attributions "
                "WHERE scheme_resource_instance_id = %s",
                [scheme_id],
            )
            cursor.execute(
                "DELETE FROM resource_x_resource WHERE resourceinstanceidfrom = %s "
                "OR resourceinstanceidto = %s",
                [scheme_id, scheme_id],
            )
            cursor.execute(
                "DELETE FROM resource_identifiers WHERE resourceid_id = %s", [scheme_id]
            )
            cursor.execute(
                "DELETE FROM resource_instances WHERE resourceinstanceid = %s",
                [scheme_id],
            )

    if orphaned_scheme_ids:
        log(f"Removed {len(orphaned_scheme_ids)} orphaned AAT scheme resource(s)")
    return orphaned_scheme_ids


def find_existing_aat_scheme_id():
    """Return the resource id of an already-loaded AAT scheme, or None.

    Identified by the Getty URI on its URI tile rather than by label, so a
    renamed scheme is still recognised.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT resourceinstanceid
              FROM tiles
             WHERE nodegroupid = '{const.SCHEME_URI_NODEGROUP}'
               AND tiledata ->> '{const.SCHEME_URI_CONTENT_NODE}' LIKE %(uri_prefix)s
             LIMIT 1
            """,
            {"uri_prefix": f"{AAT_URI_PREFIX}%"},
        )
        row = cursor.fetchone()
    return row[0] if row else None


def load_aat(
    working_directory,
    archive_path=None,
    archive_url=GETTY_AAT_EXPLICIT_ZIP_URL,
    scheme_identifier_uri=DEFAULT_SCHEME_IDENTIFIER_URI,
    scheme_pref_label=DEFAULT_SCHEME_PREF_LABEL,
    replace_existing=True,
    preserve_resource_ids=True,
    lifecycle_state_id=LOCKED_STATE_ID,
    skip_indexing=False,
    show_progress=None,
    log=print,
):
    """Download, convert and load the Getty AAT, replacing any previous load.

    Returns a dict of counts describing what was loaded.
    """
    os.makedirs(working_directory, exist_ok=True)
    skos_path = os.path.join(working_directory, SKOS_FILENAME)
    attribution_path = os.path.join(working_directory, ATTRIBUTION_FILENAME)
    snapshot_path = os.path.join(working_directory, RESOURCE_ID_SNAPSHOT_FILENAME)

    downloaded_archive_path = None
    if not archive_path:
        downloaded_archive_path = os.path.join(
            working_directory, os.path.basename(archive_url)
        )
        download_archive(downloaded_archive_path, url=archive_url, log=log)
        archive_path = downloaded_archive_path

    extraction_date = read_archive_extraction_date(archive_path)
    if extraction_date:
        log(f"Getty export was built on {extraction_date.isoformat()}")

    log("[1/6] Converting the Getty export to SKOS ...")
    concept_count = convert_archive_to_skos(
        archive_path,
        skos_path,
        scheme_identifier_uri=scheme_identifier_uri,
        scheme_pref_label=scheme_pref_label,
        show_progress=show_progress,
        log=log,
    )

    log("[2/6] Extracting source and contributor attribution ...")
    extract_attribution_from_archive(
        archive_path, attribution_path, show_progress=show_progress, log=log
    )

    log("[3/6] Ensuring the languages the data uses exist ...")
    ensure_languages(skos_path, log=log)
    repair_colliding_language_names(log=log)

    existing_scheme_id = find_existing_aat_scheme_id()
    pinned_ids_path = ""
    if existing_scheme_id:
        if preserve_resource_ids:
            snapshot_count = write_resource_id_snapshot(
                AAT_URI_PREFIX, snapshot_path, scheme_resource_id=existing_scheme_id
            )
            pinned_ids_path = snapshot_path
            log(f"Snapshotted {snapshot_count:,} existing resource ids")
        if replace_existing:
            for model_name, count in summarize_scheme_partition(
                existing_scheme_id
            ).items():
                log(f"  will remove {count:,} {model_name}")
            purge_scheme_partition(existing_scheme_id, log=log)

    log(f"[4/6] Importing {concept_count:,} concepts ...")
    call_command(
        "packages",
        operation="import_lingo_resources",
        source=skos_path,
        overwrite="overwrite",
        import_identifiers=True,
        pin_resource_ids=pinned_ids_path,
        celery_byte_size_limit=AAT_CELERY_BYTE_SIZE_LIMIT,
        lifecycle_state_id=lifecycle_state_id,
        skip_indexing=skip_indexing,
        bypass_staging=True,
    )

    log("[5/6] Loading source and contributor attribution ...")
    call_command(
        "load_aat_sources",
        source=attribution_path,
        skip_indexing=skip_indexing,
        no_progress=show_progress is False,
    )

    log("[6/6] Assigning concept types ...")
    call_command("update_aat_concept_types", source=skos_path)

    loaded_scheme_id = find_existing_aat_scheme_id()
    if loaded_scheme_id:
        remove_orphaned_aat_schemes(loaded_scheme_id, log=log)
    if loaded_scheme_id and extraction_date:
        set_scheme_attribution(loaded_scheme_id, build_aat_attribution(extraction_date))
        log("Recorded the Getty attribution statement on the scheme")

    if downloaded_archive_path and os.path.exists(downloaded_archive_path):
        os.unlink(downloaded_archive_path)

    return {
        "concepts": concept_count,
        "extraction_date": extraction_date,
        "scheme_id": loaded_scheme_id,
        "skos_path": skos_path,
        "attribution_path": attribution_path,
    }
