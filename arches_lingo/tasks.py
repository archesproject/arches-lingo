import logging
from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone
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

    try:
        run = ConceptMatchRun.objects.get(pk=run_id)
    except ConceptMatchRun.DoesNotExist:
        # The run was deleted, or the queue outlived the database it was
        # recorded in. There is nothing left to report against, and retrying
        # would only fail the same way.
        logger.warning(
            "Match run %s no longer exists; abandoning its detection task.",
            run_id,
        )
        return

    try:
        completed_run = run_detection(
            MatchScope(**scope_parameters),
            signals=tuple(signals),
            same_language_only=options["same_language_only"],
            similarity_threshold=options["similarity_threshold"],
            user=run.user,
            log=lambda message: logger.info(message),
            run=run,
        )
        if completed_run is None:
            # Deleting the run is how it is cancelled, so there is nothing left
            # to report against and nothing the reviewer is waiting to hear.
            logger.info("Match run %s was cancelled while it was working.", run_id)
            return
        message = _("Match detection found {} candidate pair(s)").format(
            completed_run.candidate_count
        )
    except Exception as exception:
        # run_detection records the failure on the run before re-raising, so a
        # run that got as far as starting already shows why. Anything raised
        # before that -- a scope this worker's code cannot understand, say --
        # would otherwise leave the run pending with nothing to explain it,
        # until it was reaped minutes later as though its worker had died.
        logger.error(exception, exc_info=True)
        ConceptMatchRun.objects.filter(
            pk=run_id, status=ConceptMatchRun.STATUS_PENDING
        ).update(
            status=ConceptMatchRun.STATUS_FAILED,
            finished=timezone.now(),
            error_message=str(exception),
        )
        message = _("Match detection failed")

    if run.user:
        notify_completion(message, run.user)
