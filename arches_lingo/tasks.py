import logging
from celery import shared_task
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from arches.app.models import models
from arches_lingo.etl_modules import migrate_to_lingo
from arches.app.tasks import notify_completion


from django_tasks import task


# @shared_task
@task
def migrate_rdm_to_lingo_task(userid, loadid, scheme_conceptid):
    logger = logging.getLogger(__name__)

    try:
        Migrator = migrate_to_lingo.RDMMtoLingoMigrator(loadid=loadid)
        Migrator.run_load_task(userid, loadid, scheme_conceptid)

        load_event = models.LoadEvent.objects.get(loadid=loadid)
        status = _("Completed") if load_event.status == "indexed" else _("Failed")
    except Exception as e:
        logger.error(e)
        load_event = models.LoadEvent.objects.get(loadid=loadid)
        load_event.status = "failed"
        load_event.save()
        status = _("Failed")
    finally:
        msg = _("RDM to Lingo Migration: [{}]").format(status)
        user = User.objects.get(id=userid)
        notify_completion(msg, user)
