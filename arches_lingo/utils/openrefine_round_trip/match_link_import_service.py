"""Starting, finding and listing match link imports for the API."""

import datetime
import uuid

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext as _

import arches.app.utils.task_management as task_management

from arches_lingo.models import MatchLinkImport
from arches_lingo.permissions import is_lingo_admin
from arches_lingo.tasks import apply_match_link_import_task
from arches_lingo.utils.openrefine_round_trip.match_link_import import (
    apply_match_link_import,
    parse_match_link_csv,
)

# An import still waiting to start, or still running, this long after it was
# created or started is presumed lost with its worker, so the dialog polling it
# stops waiting. A worker that picks up a given-up import leaves it alone.
STALE_IMPORT_SECONDS = getattr(settings, "LINGO_MATCH_LINK_IMPORT_STALE_SECONDS", 1800)
RECENT_IMPORTS_LIMIT = 25
IN_PROGRESS_STATUSES = [MatchLinkImport.STATUS_PENDING, MatchLinkImport.STATUS_RUNNING]


def parse_scheme_id(raw_scheme_id):
    if not raw_scheme_id:
        return None
    try:
        return str(uuid.UUID(raw_scheme_id))
    except ValueError:
        raise ValueError(_("The scheme id is not valid."))


def start_match_link_import(uploaded_file, user, scheme_id=None):
    """Record an import and apply it on a worker, or right away without one."""
    rows = parse_match_link_csv(uploaded_file)
    match_link_import = MatchLinkImport.objects.create(
        user=user,
        filename=(uploaded_file.name or "")[:255],
        scheme_id=scheme_id,
        rows=rows,
        language=get_language() or "",
    )
    if task_management.check_if_celery_available():
        apply_match_link_import_task.apply_async(args=[match_link_import.pk])
    else:
        apply_match_link_import(match_link_import)
    return match_link_import


def reap_stale_imports(match_link_imports):
    cutoff = timezone.now() - datetime.timedelta(seconds=STALE_IMPORT_SECONDS)
    match_link_imports.filter(
        Q(status=MatchLinkImport.STATUS_PENDING, created__lt=cutoff)
        | Q(status=MatchLinkImport.STATUS_RUNNING, started__lt=cutoff)
    ).update(
        status=MatchLinkImport.STATUS_FAILED,
        finished=timezone.now(),
        error_code=MatchLinkImport.ERROR_INTERRUPTED,
    )


def get_match_link_import(match_link_import_id, user):
    """Return the import if this user started it or is a Lingo admin, else None."""
    match_link_imports = MatchLinkImport.objects.filter(pk=match_link_import_id)
    if not is_lingo_admin(user):
        match_link_imports = match_link_imports.filter(user_id=user.pk)
    reap_stale_imports(match_link_imports)
    return match_link_imports.first()


def list_recent_match_link_imports(user):
    match_link_imports = MatchLinkImport.objects.filter(user_id=user.pk)
    reap_stale_imports(match_link_imports)
    return match_link_imports[:RECENT_IMPORTS_LIMIT]


def is_in_progress(match_link_import):
    return match_link_import.status in IN_PROGRESS_STATUSES


def describe_error(error_code):
    """Translate a stored error code in the language of whoever is reading it."""
    error_messages = {
        MatchLinkImport.ERROR_APPLY_FAILED: _(
            "The links could not be added. Nothing was changed; check the file "
            "and try again, or ask an administrator to look at the server log."
        ),
        MatchLinkImport.ERROR_INTERRUPTED: _(
            "This import stopped before it finished. The server may have been "
            "restarted while it was working; upload the file again to retry."
        ),
        MatchLinkImport.ERROR_INDEXING_FAILED: _(
            "The links were added, but the search index could not be updated. "
            "Reindex the affected concepts to find them by their new links."
        ),
    }
    return error_messages.get(error_code, "")


def serialize_match_link_import(match_link_import):
    return {
        "id": match_link_import.pk,
        "filename": match_link_import.filename,
        "status": match_link_import.status,
        "scheme_id": (
            str(match_link_import.scheme_id) if match_link_import.scheme_id else None
        ),
        "created": match_link_import.created.isoformat(),
        "finished": (
            match_link_import.finished.isoformat()
            if match_link_import.finished
            else None
        ),
        "total_rows": len(match_link_import.rows),
        "outcome_counts": match_link_import.outcome_counts,
        "error_message": describe_error(match_link_import.error_code),
    }
