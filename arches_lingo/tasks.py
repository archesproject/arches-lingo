import logging
from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext as _
from arches.app.models import models
from arches_lingo.etl_modules import migrate_to_lingo
from arches_lingo.models import ConceptMatchRun
from arches_lingo.utils.concept_matching import MatchScope, run_detection
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
    """Fill in a run the request has already created and returned to the caller."""
    logger = logging.getLogger(__name__)

    try:
        run = ConceptMatchRun.objects.get(pk=run_id)
    except ConceptMatchRun.DoesNotExist:
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
            logger.info("Match run %s was cancelled while it was working.", run_id)
            return
        message = _("Match detection found {} candidate pair(s)").format(
            completed_run.candidate_count
        )
    except Exception as exception:
        # run_detection records its own failures; this covers anything earlier.
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
