"""Previewing, starting and finding match link imports for the API."""

import datetime
import uuid

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import formats, timezone
from django.utils.translation import get_language
from django.utils.translation import gettext as _

import arches.app.utils.task_management as task_management

from arches_lingo.models import MatchLinkImport
from arches_lingo.permissions import is_lingo_admin
from arches_lingo.tasks import apply_match_link_import_task
from arches_lingo.utils.openrefine_round_trip.exceptions import (
    RoundTripRequestError,
)
from arches_lingo.utils.openrefine_round_trip.match_link_csv import (
    parse_match_link_csv,
)
from arches_lingo.utils.openrefine_round_trip.match_link_import import (
    apply_match_link_import,
)
from arches_lingo.utils.openrefine_round_trip.match_link_validation import (
    OUTCOME_UNKNOWN_CONCEPT,
    count_outcomes,
    validate_match_links,
)
from arches_lingo.utils.reconciliation.concept_summaries import (
    get_display_labels_for_concepts,
)

# An import still running this long after it started is presumed lost with its
# worker, so the dialog polling it stops waiting. A worker that picks up a
# given-up import leaves it alone.
STALE_IMPORT_SECONDS = getattr(settings, "LINGO_MATCH_LINK_IMPORT_STALE_SECONDS", 1800)
# Waiting to start is given longer: a queue backed up behind other long tasks
# is not a lost worker.
STALE_PENDING_IMPORT_SECONDS = getattr(
    settings, "LINGO_MATCH_LINK_IMPORT_STALE_PENDING_SECONDS", 6 * 60 * 60
)
# Without a worker the links are written inside the request, so a file is kept
# small enough to finish well inside a proxy timeout.
MAX_LINKS_WITHOUT_WORKER = getattr(
    settings, "LINGO_MATCH_LINK_IMPORT_MAX_LINKS_WITHOUT_WORKER", 500
)
IN_PROGRESS_STATUSES = [MatchLinkImport.STATUS_PENDING, MatchLinkImport.STATUS_RUNNING]


def parse_scheme_id(raw_scheme_id):
    if not raw_scheme_id:
        return None
    try:
        return str(uuid.UUID(raw_scheme_id))
    except ValueError:
        raise RoundTripRequestError(_("The scheme id is not valid."))


def discard_unapplied_previews(user):
    """A requester's earlier previews are superseded by their next upload."""
    MatchLinkImport.objects.filter(user=user, apply_requested__isnull=True).delete()


def preview_match_link_import(uploaded_file, user, scheme_id=None):
    """Record the uploaded links as an import awaiting the requester's
    go-ahead, and report what applying it would do with each link."""
    match_links = parse_match_link_csv(uploaded_file)
    discard_unapplied_previews(user)
    match_link_import = MatchLinkImport.objects.create(
        user=user,
        filename=(uploaded_file.name or "")[:255],
        scheme_id=scheme_id,
        links=match_links,
        link_count=len(match_links),
        language=get_language() or "",
    )
    validated_links = validate_match_links(match_links, user, scheme_id)
    concept_label_by_id = get_display_labels_for_concepts(
        {
            validated_link["concept_id"]
            for validated_link in validated_links
            if validated_link["outcome"] != OUTCOME_UNKNOWN_CONCEPT
        },
        get_language(),
    )
    return {
        "import_id": match_link_import.pk,
        "total_links": len(validated_links),
        "counts_by_outcome": count_outcomes(validated_links),
        "links": [
            {
                **validated_link,
                "concept_label": concept_label_by_id.get(validated_link["concept_id"]),
            }
            for validated_link in validated_links
        ],
    }


def start_match_link_import(match_link_import_id, user):
    """Apply the requester's previewed import on a worker, or right away
    without one."""
    # Raising inside the transaction withdraws the claim on the import.
    with transaction.atomic():
        # One update, so two requests for the same import cannot both start it.
        is_start_claimed = MatchLinkImport.objects.filter(
            pk=match_link_import_id,
            user=user,
            status=MatchLinkImport.STATUS_PENDING,
            apply_requested__isnull=True,
        ).update(apply_requested=timezone.now())
        if not is_start_claimed:
            raise RoundTripRequestError(
                _(
                    "That import was not found, or has already been started. "
                    "Upload the file again."
                )
            )
        match_link_import = MatchLinkImport.objects.get(pk=match_link_import_id)
        is_celery_available = task_management.check_if_celery_available()
        if (
            not is_celery_available
            and match_link_import.link_count > MAX_LINKS_WITHOUT_WORKER
        ):
            raise RoundTripRequestError(
                _(
                    "Without a background worker, at most %(limit)s links can be "
                    "imported at once. Split the file into smaller ones, or ask "
                    "an administrator to start a Celery worker."
                )
                % {
                    "limit": formats.number_format(
                        MAX_LINKS_WITHOUT_WORKER, force_grouping=True
                    )
                }
            )
    if is_celery_available:
        apply_match_link_import_task.apply_async(args=[match_link_import.pk])
    else:
        apply_match_link_import(match_link_import)
    return match_link_import


def reap_stale_imports(match_link_imports):
    now = timezone.now()
    match_link_imports.filter(
        Q(
            status=MatchLinkImport.STATUS_PENDING,
            apply_requested__lt=now
            - datetime.timedelta(seconds=STALE_PENDING_IMPORT_SECONDS),
        )
        | Q(
            status=MatchLinkImport.STATUS_RUNNING,
            started__lt=now - datetime.timedelta(seconds=STALE_IMPORT_SECONDS),
        )
    ).update(
        status=MatchLinkImport.STATUS_FAILED,
        finished=now,
        error_code=MatchLinkImport.ERROR_INTERRUPTED,
    )


def get_match_link_import(match_link_import_id, user):
    """Return the import if this user started it or is a Lingo admin, else None."""
    match_link_imports = MatchLinkImport.objects.filter(pk=match_link_import_id)
    if not is_lingo_admin(user):
        match_link_imports = match_link_imports.filter(user_id=user.pk)
    reap_stale_imports(match_link_imports)
    # The links are not needed to report on an import, and can be large.
    return match_link_imports.defer("links").first()


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
            "This import did not finish in the expected time, so nothing was "
            "changed. The server may have been restarted while it was working; "
            "upload the file again to retry."
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
        "total_links": match_link_import.link_count,
        "outcome_counts": match_link_import.outcome_counts,
        "error_message": describe_error(match_link_import.error_code),
    }
