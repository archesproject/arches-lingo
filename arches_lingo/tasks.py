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
    status = _("Completed")

    try:
        from arches_lingo.etl_modules.lingo_resource_exporter import (
            LingoResourceExporter,
        )

        exporter = LingoResourceExporter()
        exporter.user = User.objects.get(id=userid)
        exporter.loadid = loadid
        exporter.load_event = models.LoadEvent.objects.get(loadid=loadid)
        exporter.run_export_task(resourceid, filename, format)
        load_event = models.LoadEvent.objects.get(loadid=loadid)
        status = _("Completed") if load_event.status == "indexed" else _("Failed")
    except Exception as e:
        logger.error(e, exc_info=True)
        status = _("Failed")
        try:
            load_event = models.LoadEvent.objects.get(loadid=loadid)
            load_event.status = "failed"
            load_event.error_message = str(e)
            load_event.save()
        except Exception:
            pass
    finally:
        msg = _("Lingo Export: [{}]").format(status)
        user = User.objects.get(id=userid)
        notify_completion(msg, user)


@shared_task
def load_lingo_resources_task(loadid, userid, kwargs={}):
    logger = logging.getLogger(__name__)
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
