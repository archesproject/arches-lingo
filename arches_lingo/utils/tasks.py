from datetime import datetime

from celery import app, Celery
from django.db import connection
from django.utils.translation import gettext as _

from arches.app.models.models import LoadEvent
import arches.app.utils.task_management as task_management


ITEMS_PER_PAGE = 20


def get_user_load_events(user, page=1):
    """Return a page of LoadEvents belonging to the given user, newest first."""
    all_events = (
        LoadEvent.objects.filter(user=user)
        .select_related("etl_module")
        .order_by("-load_start_time")
    )

    total = all_events.count()
    offset = (page - 1) * ITEMS_PER_PAGE
    page_events = all_events[offset : offset + ITEMS_PER_PAGE]

    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    events = []
    for event in page_events:
        events.append(_serialize_load_event(event))

    return {
        "events": events,
        "paginator": {
            "total": total,
            "total_pages": total_pages,
            "current_page": page,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        },
    }


def cancel_user_load_event(user, loadid):
    """
    Send a cancellation request to Celery for a running task owned by the given user.
    Returns a dict with success status and a message.
    """
    try:
        load_event = LoadEvent.objects.get(loadid=loadid, user=user)
    except LoadEvent.DoesNotExist:
        return {"success": False, "message": _("Task not found.")}

    if load_event.complete:
        return {
            "success": False,
            "message": _("Task is already complete and cannot be cancelled."),
        }

    if not task_management.check_if_celery_available():
        return {
            "success": False,
            "message": _("Unable to cancel: Celery does not appear to be running."),
        }

    celery_app = Celery()
    remote_control = app.control.Control(app=celery_app)
    remote_control.revoke(task_id=load_event.taskid, terminate=True)

    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE load_event SET status = %s, load_end_time = %s WHERE loadid = %s",
            ("cancelled", datetime.now(), loadid),
        )

    load_event.refresh_from_db()
    return {"success": True, "event": _serialize_load_event(load_event)}


def delete_user_load_event(user, loadid):
    """
    Delete a completed LoadEvent (and its associated staging/error rows) owned by
    the given user.  Only completed or cancelled events may be deleted.
    """
    try:
        load_event = LoadEvent.objects.get(loadid=loadid, user=user)
    except LoadEvent.DoesNotExist:
        return {"success": False, "message": _("Task not found.")}

    if not load_event.complete and load_event.status not in (
        "cancelled",
        "failed",
    ):
        return {
            "success": False,
            "message": _("Only completed or cancelled tasks can be deleted."),
        }

    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM load_errors WHERE loadid = %s", [loadid])
        cursor.execute("DELETE FROM load_staging WHERE loadid = %s", [loadid])
        cursor.execute("DELETE FROM load_event WHERE loadid = %s", [loadid])

    return {"success": True}


def _serialize_load_event(event):
    return {
        "loadid": str(event.loadid),
        "status": event.status,
        "complete": event.complete,
        "successful": event.successful,
        "load_description": event.load_description,
        "load_details": event.load_details,
        "error_message": event.error_message,
        "load_start_time": (
            event.load_start_time.isoformat() if event.load_start_time else None
        ),
        "load_end_time": (
            event.load_end_time.isoformat() if event.load_end_time else None
        ),
        "etl_module": {
            "name": event.etl_module.name if event.etl_module_id else None,
            "etl_type": event.etl_module.etl_type if event.etl_module_id else None,
        },
    }
