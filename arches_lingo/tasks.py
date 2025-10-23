import logging
from celery import shared_task
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from arches.app.models import models
from arches_lingo.etl_modules import migrate_to_lingo
from arches.app.tasks import notify_completion


@shared_task
def load_lingo_resources_task(**kwargs):
    logger = logging.getLogger(__name__)

    try:
        importer = kwargs.get("importer")
        importer.run_load_task()
        load_event = models.LoadEvent.objects.get(loadid=importer.loadid)
        status = _("Completed") if load_event.status == "indexed" else _("Failed")
    except Exception as e:
        logger.error(e)
        load_event = models.LoadEvent.objects.get(loadid=importer.loadid)
        load_event.status = "failed"
        load_event.save()
        status = _("Failed")
    finally:
        msg = _("Lingo Resource Importer: [{}]").format(status)
        user = User.objects.get(id=importer.userid)
        notify_completion(msg, user)
