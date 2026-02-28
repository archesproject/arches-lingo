import logging
from celery import shared_task
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from arches.app.models import models
from arches_lingo.etl_modules import migrate_to_lingo
from arches.app.tasks import notify_completion

logger = logging.getLogger(__name__)


@shared_task
def load_lingo_resources_task(loadid, userid, kwargs={}):
    status = _("Started")

    try:
        importer = migrate_to_lingo.LingoResourceImporter(
            loadid=loadid, userid=userid, **kwargs
        )
        importer.run_load_task()
        load_event = models.LoadEvent.objects.get(loadid=loadid)
        status = _("Completed") if load_event.status == "indexed" else _("Failed")
    except Exception as e:
        logger.error(e)
        load_event = models.LoadEvent.objects.get(loadid=loadid)
        load_event.status = "failed"
        load_event.save()
        status = _("Failed")
    finally:
        msg = _("Lingo Resource Importer: [{}]").format(status)
        user = User.objects.get(id=userid)
        notify_completion(msg, user)


@shared_task
def export_lingo_resources_task(loadid, userid, resourceid, filename, format_type):
    """Run a Lingo resource export as a background Celery task.

    This is used to defer expensive exports (e.g. JSON-LD) outside the
    HTTP request thread.  On success the exporter's ``_finalize_export``
    handles user notification; on failure we notify explicitly here.
    """
    from arches_lingo.etl_modules.lingo_resource_exporter import LingoResourceExporter

    try:
        exporter = LingoResourceExporter()
        exporter.user = User.objects.get(id=userid)
        exporter.loadid = loadid
        exporter.moduleid = models.ETLModule.objects.get(
            slug="export-lingo-resources"
        ).pk
        exporter.load_event = models.LoadEvent.objects.get(loadid=loadid)
        exporter.resourceid = resourceid
        exporter.run_export_task(resourceid, filename, format_type)
    except Exception as e:
        logger.error(e)
        try:
            load_event = models.LoadEvent.objects.get(loadid=loadid)
            load_event.status = "failed"
            load_event.error_message = str(e)
            load_event.save()
        except Exception:
            pass
        msg = _("Lingo Resource Exporter: [Failed]")
        user = User.objects.get(id=userid)
        notify_completion(msg, user)
