"""Run the Getty AAT load end to end.

The load is a sequence of steps that must happen in order: the SKOS conversion
produces the file the language step scans and the importer reads, and attribution
cannot be attached until the concepts it refers to exist. Each step is exposed
separately so a caller can resume after a failure without repeating the slow
download and conversion.
"""

import os
from xml.etree import ElementTree

from django.core.management import call_command
from django.db import connection, transaction

from arches.app.models.models import GraphModel
from arches_controlled_lists.models import ListItem

import arches_lingo
from arches_lingo import const
from arches_lingo.utils.aat.attribution_extraction import (
    extract_attribution_from_archive,
)
from arches_lingo.utils.aat.attribution_statement import (
    build_aat_attribution,
    set_scheme_attribution,
)
from arches_lingo.utils.aat.concept_types import (
    MissingConceptTypeItemsError,
    load_non_concept_type_items,
)
from arches_lingo.utils.aat.deferred_indexing import (
    index_resources,
    remove_resources_from_index,
)
from arches_lingo.utils.aat.languages import (
    ensure_languages,
    repair_colliding_language_names,
)
from arches_lingo.utils.aat.resource_id_pinning import write_resource_id_snapshot
from arches_lingo.utils.aat.scheme_partition import (
    list_scheme_partition_resource_ids,
    purge_scheme_partition,
    summarize_scheme_partition,
)
from arches_lingo.utils.concept_lifecycle import LOCKED_STATE_ID
from arches_lingo.utils.skos import GVP_TYPED_RELATION_PREFIX
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

RELATED_PROPERTIES_LIST_PATH = os.path.join(
    os.path.dirname(arches_lingo.__file__),
    "pkg",
    "reference_data",
    "controlled_lists",
    "related_properties.xml",
)
DCTERMS_IDENTIFIER_TAG = "{http://purl.org/dc/terms/}identifier"


class LoadPreconditionError(Exception):
    """Raised when the database or the options given rule the load out."""


def find_existing_aat_scheme_id(scheme_identifier_uri):
    """Return the resource id of an already-loaded AAT scheme, or None.

    Identified by the identifier URI the load gave the scheme rather than by
    label, so a renamed scheme is still recognised.

    Raises LoadPreconditionError when more than one scheme carries the URI,
    rather than picking one to purge.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT DISTINCT resourceinstanceid
              FROM tiles
             WHERE nodegroupid = '{const.SCHEME_URI_NODEGROUP}'
               AND tiledata ->> '{const.SCHEME_URI_CONTENT_NODE}' = %(scheme_uri)s
            """,
            {"scheme_uri": scheme_identifier_uri},
        )
        scheme_ids = [scheme_id for (scheme_id,) in cursor.fetchall()]
    if len(scheme_ids) > 1:
        raise LoadPreconditionError(
            f"{len(scheme_ids)} schemes are identified by {scheme_identifier_uri} "
            f"({', '.join(str(scheme_id) for scheme_id in scheme_ids)}). Remove "
            "all but one before reloading, so the load knows which to replace."
        )
    return scheme_ids[0] if scheme_ids else None


def check_reference_data_is_loaded():
    """Fail before any work when the reference data the load needs is absent.

    The load takes hours and its last step refuses to run without the term
    types the AAT concept types are drawn from. Checking that up front stops a
    run that would otherwise download the export, insert languages and write
    every concept before discovering the package was never loaded. The relation
    types are checked too, since without them the import succeeds but every
    typed relation comes in untyped.
    """
    missing_graph_names = [
        graph_name
        for graph_name, graph_id in (
            ("Concept", const.CONCEPTS_GRAPH_ID),
            ("Scheme", const.SCHEMES_GRAPH_ID),
        )
        if not GraphModel.objects.filter(pk=graph_id).exists()
    ]
    if missing_graph_names:
        raise LoadPreconditionError(
            f"The {' and '.join(missing_graph_names)} resource model(s) are not "
            "in the database. Load the Lingo package before loading the AAT."
        )

    # Both lists are reported together so following the message once is enough.
    problems = []
    try:
        load_non_concept_type_items()
    except MissingConceptTypeItemsError as missing_items_error:
        problems.append(str(missing_items_error))
    missing_relation_type_count = len(find_missing_gvp_relation_types())
    if missing_relation_type_count:
        problems.append(
            f"{missing_relation_type_count} Getty relation types are missing "
            "from the related properties list, so typed relations would load "
            f"untyped. Load {RELATED_PROPERTIES_LIST_PATH} to add them."
        )
    if problems:
        raise LoadPreconditionError(" ".join(problems))


def find_missing_gvp_relation_types():
    """Return the Getty relation type URIs Lingo ships but the database lacks.

    The importer leaves a relation untyped rather than failing when its
    predicate has no list item, so a stale list would otherwise go unnoticed.
    """
    shipped_relation_type_uris = {
        identifier.text.strip()
        for identifier in ElementTree.parse(RELATED_PROPERTIES_LIST_PATH).iter(
            DCTERMS_IDENTIFIER_TAG
        )
        if identifier.text
        and identifier.text.strip().startswith(GVP_TYPED_RELATION_PREFIX)
    }
    loaded_relation_type_uris = set(
        ListItem.objects.filter(
            list_id=const.RELATED_PROPERTIES_LIST_ID,
            uri__in=shipped_relation_type_uris,
        ).values_list("uri", flat=True)
    )
    return shipped_relation_type_uris - loaded_relation_type_uris


def load_aat(
    working_directory,
    archive_path=None,
    archive_url=GETTY_AAT_EXPLICIT_ZIP_URL,
    scheme_identifier_uri=DEFAULT_SCHEME_IDENTIFIER_URI,
    scheme_pref_label=DEFAULT_SCHEME_PREF_LABEL,
    preserve_resource_ids=True,
    lifecycle_state_id=LOCKED_STATE_ID,
    skip_indexing=False,
    show_progress=None,
    log=print,
):
    """Download, convert and load the Getty AAT, replacing any previous load.

    Returns a dict of counts describing what was loaded.
    """
    check_reference_data_is_loaded()

    existing_scheme_id = find_existing_aat_scheme_id(scheme_identifier_uri)
    step_count = 6 if skip_indexing else 7

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

    log(f"[1/{step_count}] Converting the Getty export to SKOS ...")
    concept_count = convert_archive_to_skos(
        archive_path,
        skos_path,
        scheme_identifier_uri=scheme_identifier_uri,
        scheme_pref_label=scheme_pref_label,
        show_progress=show_progress,
        log=log,
    )

    log(f"[2/{step_count}] Extracting source and contributor attribution ...")
    extract_attribution_from_archive(
        archive_path, attribution_path, show_progress=show_progress, log=log
    )

    log(f"[3/{step_count}] Ensuring the languages the data uses exist ...")
    ensure_languages(skos_path, log=log)
    repair_colliding_language_names(log=log)

    pinned_ids_path = ""
    if existing_scheme_id:
        snapshot_count = write_resource_id_snapshot(
            AAT_URI_PREFIX,
            snapshot_path,
            existing_scheme_id,
            include_concepts=preserve_resource_ids,
        )
        pinned_ids_path = snapshot_path
        log(f"Snapshotted {snapshot_count:,} existing resource ids")

    log(f"[4/{step_count}] Importing {concept_count:,} concepts ...")
    # Removing the previous load and writing the new one share a transaction so
    # a failed import leaves the vocabulary as it was rather than deleted.
    previous_resource_ids = set()
    with transaction.atomic():
        if existing_scheme_id:
            if not skip_indexing:
                previous_resource_ids = list_scheme_partition_resource_ids(
                    existing_scheme_id
                )
            for model_name, count in summarize_scheme_partition(
                existing_scheme_id
            ).items():
                log(f"  will remove {count:,} {model_name}")
            purge_scheme_partition(existing_scheme_id, log=log)

        call_command(
            "packages",
            operation="import_lingo_resources",
            source=skos_path,
            overwrite="overwrite",
            import_identifiers=True,
            pin_resource_ids=pinned_ids_path,
            celery_byte_size_limit=AAT_CELERY_BYTE_SIZE_LIMIT,
            lifecycle_state_id=lifecycle_state_id,
            skip_indexing=True,
            bypass_staging=True,
        )

    log(f"[5/{step_count}] Loading source and contributor attribution ...")
    call_command(
        "load_aat_sources",
        source=attribution_path,
        skip_indexing=True,
        no_progress=show_progress is False,
    )

    log(f"[6/{step_count}] Assigning concept types ...")
    call_command("update_aat_concept_types", source=skos_path)

    loaded_scheme_id = find_existing_aat_scheme_id(scheme_identifier_uri)
    if loaded_scheme_id and extraction_date:
        set_scheme_attribution(loaded_scheme_id, build_aat_attribution(extraction_date))
        log("Recorded the Getty attribution statement on the scheme")

    # Indexing waits until the attribution and concept type steps have changed
    # the concept tiles, so each document is written once, from the end state.
    if not skip_indexing:
        log(f"[7/{step_count}] Indexing the loaded resources ...")
        loaded_resource_ids = (
            list_scheme_partition_resource_ids(loaded_scheme_id)
            if loaded_scheme_id
            else set()
        )
        remove_resources_from_index(
            previous_resource_ids - loaded_resource_ids, log=log
        )
        index_resources(list(loaded_resource_ids), log=log)

    if downloaded_archive_path and os.path.exists(downloaded_archive_path):
        os.unlink(downloaded_archive_path)

    return {
        "concepts": concept_count,
        "extraction_date": extraction_date,
        "scheme_id": loaded_scheme_id,
        "skos_path": skos_path,
        "attribution_path": attribution_path,
    }
