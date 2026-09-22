import logging
from celery import shared_task
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from arches.app.models import models
from arches_lingo.etl_modules import migrate_to_lingo
from arches.app.tasks import notify_completion


@shared_task
def export_lingo_resources_task(
    loadid, userid, resourceid, filename=None, format="xml"
):
    logger = logging.getLogger(__name__)

    try:
        from arches_lingo.etl_modules.lingo_resource_exporter import (
            LingoResourceExporter,
        )

        exporter = LingoResourceExporter()
        exporter.user = User.objects.get(id=userid)
        exporter.loadid = loadid
        exporter.load_event = models.LoadEvent.objects.get(loadid=loadid)
        exporter.run_export_task(resourceid, filename, format)
        # _finalize_export (success) and handle_error (internal failure)
        # both call notify_completion directly
    except Exception as exception:
        logger.error(exception, exc_info=True)
        user = User.objects.get(id=userid)
        scheme_name = ""
        try:
            load_event = models.LoadEvent.objects.get(loadid=loadid)
            load_event.status = "failed"
            load_event.error_message = str(exception)
            load_event.save()
            if isinstance(load_event.load_details, dict):
                scheme_name = load_event.load_details.get("scheme_name", "")
        except Exception:
            pass
        message = (
            _("{} export failed").format(scheme_name)
            if scheme_name
            else _("Export failed")
        )
        notify_completion(message, user)


@shared_task
def load_lingo_resources_task(loadid, userid, kwargs={}):
    logger = logging.getLogger(__name__)

    try:
        importer = migrate_to_lingo.LingoResourceImporter(
            loadid=loadid, userid=userid, **kwargs
        )
        importer.run_load_task()
        # _finalize_import (called within run_load_task) handles notify_completion
    except Exception as exception:
        logger.error(exception, exc_info=True)
        user = User.objects.get(id=userid)
        thesaurus_name = ""
        try:
            load_event = models.LoadEvent.objects.get(loadid=loadid)
            load_event.status = "failed"
            load_event.error_message = str(exception)
            load_event.save()
            if isinstance(load_event.load_details, dict):
                thesaurus_name = load_event.load_details.get("thesaurus_name", "")
        except Exception:
            pass
        message = (
            _("{} import failed").format(thesaurus_name)
            if thesaurus_name
            else _("Import failed")
        )
        notify_completion(message, user)


@shared_task
def detect_concept_matches_task(run_id, scope_parameters, signals, options):
    """Run match detection for a run that has already been handed to the caller.

    Only the fuzzy signal needs this: comparing every label in a vocabulary to
    every other takes minutes, which is far too long to hold a request open.
    The run row is the progress report -- it is created before the task is
    queued, so the interface has something to poll from the moment it asks.
    """
    logger = logging.getLogger(__name__)

    from arches_lingo.models import ConceptMatchRun
    from arches_lingo.utils.concept_matching import MatchScope, run_detection

    run = ConceptMatchRun.objects.get(pk=run_id)
    try:
        run_detection(
            MatchScope(**scope_parameters),
            signals=tuple(signals),
            same_language_only=options["same_language_only"],
            similarity_threshold=options["similarity_threshold"],
            user=run.user,
            log=lambda message: logger.info(message),
            run=run,
        )
        message = _("Match detection found {} candidate pair(s)").format(
            ConceptMatchRun.objects.get(pk=run_id).candidate_count
        )
    except Exception as exception:
        # run_detection records the failure on the run before re-raising, so the
        # interface already shows why; this is the notification and the traceback.
        logger.error(exception, exc_info=True)
        message = _("Match detection failed")

    if run.user:
        notify_completion(message, run.user)
