"""Review-side operations on match runs and their candidates."""

import datetime
import uuid
from collections import defaultdict
from http import HTTPStatus

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext as _

from arches.app.models.models import ResourceInstance

import arches.app.utils.task_management as task_management

from arches_lingo.models import ConceptMatchCandidate, ConceptMatchRun
from arches_lingo.tasks import detect_concept_matches_task
from arches_lingo.utils.concept_builder import ConceptBuilder
from arches_lingo.utils.concept_lifecycle import (
    LOCKED_STATE_ID,
    index_concepts_in_transaction,
)
from arches_lingo.utils.concept_matching import (
    DEFAULT_SIMILARITY_THRESHOLD,
    EXACT_SIGNALS,
    MatchScope,
    get_scheme_ids_for_concepts,
    mark_pairs_settled,
    restore_dismissed,
    validate_detection_options,
)
from arches_lingo.utils.concept_merge.tiles import (
    get_concept_uri,
    write_exact_match_tiles,
)
from arches_lingo.utils.concept_merge.validation import concept_is_writable

DEFAULT_ITEMS_PER_PAGE = 50
MAX_ITEMS_PER_PAGE = 200

# Linking writes up to two tiles per pair through the full tile save path.
MAX_LINK_BATCH = 200

# Well clear of HEARTBEAT_INTERVAL_SECONDS.
STALE_RUN_SECONDS = getattr(settings, "LINGO_MATCH_STALE_SECONDS", 300)

# A queue with its own worker keeps a long fuzzy run from blocking imports and
# exports on a solo-pool worker.
MATCH_TASK_QUEUE = getattr(settings, "LINGO_MATCH_TASK_QUEUE", None)

# A running slice can commit pairs between the delete clearing them and the
# delete committing, failing it on the foreign key; retrying collects them.
DELETE_RUN_ATTEMPTS = 3


class ConceptMatchRequestError(Exception):

    def __init__(self, title, message, status=HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.title = title
        self.message = message
        self.status = status


def get_run(run_id):
    try:
        return ConceptMatchRun.objects.select_related("user").get(pk=run_id)
    except ConceptMatchRun.DoesNotExist:
        raise ConceptMatchRequestError(
            _("Not found."), _("Match run not found."), status=HTTPStatus.NOT_FOUND
        )


def _was_started_by(run, user):
    return run.user_id is not None and run.user_id == getattr(user, "pk", None)


def user_can_delete_run(run, user, user_is_lingo_admin):
    """Deleting also cancels a run, so it is limited to its creator or an admin."""
    return user_is_lingo_admin or _was_started_by(run, user)


def delete_run(run, user, user_is_lingo_admin):
    if not user_can_delete_run(run, user, user_is_lingo_admin):
        raise ConceptMatchRequestError(
            _("Cannot delete this run."),
            _("Only the editor who started a run, or a Lingo admin, can delete it."),
            status=HTTPStatus.FORBIDDEN,
        )
    for attempt in range(1, DELETE_RUN_ATTEMPTS + 1):
        try:
            run.delete()
            return
        except IntegrityError:
            if attempt == DELETE_RUN_ATTEMPTS:
                raise


def _describe_creator(user):
    if user is None:
        return None
    return user.get_full_name() or user.username


def _serialize_timestamp(value):
    """With USE_TZ off the value is naive; add the offset for the browser."""
    if value is None:
        return None
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    return value.isoformat()


def _counts_by_status_for_runs(run_ids):
    counts_by_run_id = {
        run_id: {status: 0 for status, _label in ConceptMatchCandidate.STATUS_CHOICES}
        for run_id in run_ids
    }
    for row in (
        ConceptMatchCandidate.objects.filter(run_id__in=run_ids)
        .values("run_id", "status")
        .annotate(count=Count("pk"))
    ):
        counts_by_run_id[row["run_id"]][row["status"]] = row["count"]
    return counts_by_run_id


def list_runs(user, user_is_lingo_admin):
    runs = list(ConceptMatchRun.objects.select_related("user"))
    counts_by_run_id = _counts_by_status_for_runs([run.pk for run in runs])
    return [
        serialize_run(
            run, user, user_is_lingo_admin, counts_by_status=counts_by_run_id[run.pk]
        )
        for run in runs
    ]


def serialize_run(run, user=None, user_is_lingo_admin=False, counts_by_status=None):
    # Computed server-side so both ends come from one clock.
    ended_at = run.finished or timezone.now()

    if counts_by_status is None:
        counts_by_status = _counts_by_status_for_runs([run.pk])[run.pk]

    return {
        "id": run.pk,
        "name": run.name,
        "status": run.status,
        "created": _serialize_timestamp(run.created),
        "finished": _serialize_timestamp(run.finished),
        "elapsed_seconds": max(0, int((ended_at - run.created).total_seconds())),
        "parameters": run.parameters,
        "candidate_count": run.candidate_count,
        "error_message": run.error_message,
        "created_by": _describe_creator(run.user),
        "started_by_viewer": _was_started_by(run, user),
        "can_delete": user_can_delete_run(run, user, user_is_lingo_admin),
        "counts_by_status": counts_by_status,
        "pending_count": counts_by_status[ConceptMatchCandidate.STATUS_PENDING],
    }


def worker_is_available():
    """Whether a background worker would pick up a run queued now.

    A busy solo-pool worker cannot answer a ping, so a run still reporting
    progress also counts as evidence of a live worker.
    """
    if task_management.check_if_celery_available():
        return True

    cutoff = timezone.now() - datetime.timedelta(seconds=STALE_RUN_SECONDS)
    return ConceptMatchRun.objects.filter(
        status=ConceptMatchRun.STATUS_RUNNING, last_progress__gte=cutoff
    ).exists()


def reap_stale_runs(run_ids=None):
    """Fail runs that stopped reporting, returning how many were closed out.

    Celery acks a task on receipt, so a worker restarted mid-run cannot fail
    its own run. Runs with no heartbeat yet fall back to their creation time.
    """
    cutoff = timezone.now() - datetime.timedelta(seconds=STALE_RUN_SECONDS)
    stale_runs = ConceptMatchRun.objects.filter(
        Q(last_progress__lt=cutoff) | Q(last_progress__isnull=True, created__lt=cutoff),
        status__in=[ConceptMatchRun.STATUS_PENDING, ConceptMatchRun.STATUS_RUNNING],
    )
    if run_ids is not None:
        stale_runs = stale_runs.filter(pk__in=run_ids)
    return stale_runs.update(
        status=ConceptMatchRun.STATUS_FAILED,
        finished=timezone.now(),
        error_message=_(
            "This run stopped reporting progress and was presumed interrupted. "
            "The server may have been restarted while it was working."
        ),
    )


# Reported apart because the remedies differ: the concept's lifecycle state,
# or its scheme's.
CANNOT_RECEIVE_NOT_EDITABLE = "not_editable"
CANNOT_RECEIVE_SCHEME_LOCKED = "scheme_locked"


def _reasons_concepts_cannot_receive_data(
    concept_ids, scheme_ids_by_concept_id, user_is_lingo_admin
):
    """``concept_is_writable`` for a whole page at once; absent means writable."""
    editable_ids = {
        str(concept_id)
        for concept_id in ResourceInstance.objects.filter(
            pk__in=concept_ids,
            resource_instance_lifecycle_state__can_edit_resource_instances=True,
        ).values_list("pk", flat=True)
    }
    reasons = {
        concept_id: CANNOT_RECEIVE_NOT_EDITABLE
        for concept_id in concept_ids
        if concept_id not in editable_ids
    }
    if user_is_lingo_admin:
        return reasons

    locked_scheme_ids = {
        str(scheme_id)
        for scheme_id in ResourceInstance.objects.filter(
            pk__in={
                scheme_id
                for scheme_id in scheme_ids_by_concept_id.values()
                if scheme_id
            },
            resource_instance_lifecycle_state_id=LOCKED_STATE_ID,
        ).values_list("pk", flat=True)
    }
    for concept_id in concept_ids:
        if concept_id not in reasons and (
            scheme_ids_by_concept_id.get(concept_id) in locked_scheme_ids
        ):
            reasons[concept_id] = CANNOT_RECEIVE_SCHEME_LOCKED
    return reasons


def _build_concept_summaries(concept_ids, user_is_lingo_admin=False):
    """Return {concept id: {labels, scheme, whether it can be merged into}}.

    Labels rather than the descriptor, so the client picks one by language.
    """
    if not concept_ids:
        return {}

    existing_concept_ids = {
        str(concept_id)
        for concept_id in ResourceInstance.objects.filter(
            pk__in=concept_ids
        ).values_list("pk", flat=True)
    }
    # Deleted concepts are reported as missing rather than nameless.
    concept_ids = existing_concept_ids
    if not concept_ids:
        return {}

    builder = ConceptBuilder(list(concept_ids))
    scheme_ids_by_concept_id = get_scheme_ids_for_concepts(concept_ids)
    cannot_receive_reasons = _reasons_concepts_cannot_receive_data(
        concept_ids, scheme_ids_by_concept_id, user_is_lingo_admin
    )

    scheme_names_by_id = {
        str(scheme.pk): scheme.name
        for scheme in ResourceInstance.objects.filter(
            pk__in=set(scheme_ids_by_concept_id.values())
        )
    }

    summaries = {}
    for concept_id in concept_ids:
        scheme_id = scheme_ids_by_concept_id.get(concept_id)
        summaries[concept_id] = {
            "id": concept_id,
            "labels": [
                builder.serialize_concept_label(label_tile)
                for label_tile in builder.labels[concept_id]
            ],
            "scheme_id": scheme_id,
            "scheme_name": scheme_names_by_id.get(scheme_id),
            "can_receive_data": concept_id not in cannot_receive_reasons,
            "cannot_receive_reason": cannot_receive_reasons.get(concept_id),
        }
    return summaries


def _parse_positive_integer(value, default, parameter_name):
    if value in (None, ""):
        return default
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        parsed_value = 0
    if parsed_value < 1:
        raise ConceptMatchRequestError(
            _("Invalid request."),
            _("%(parameter)s must be a positive whole number.")
            % {"parameter": parameter_name},
        )
    return parsed_value


def serialize_candidate_page(
    run, status=None, page_number=1, items_per_page=None, user_is_lingo_admin=False
):
    items_per_page = min(
        _parse_positive_integer(items_per_page, DEFAULT_ITEMS_PER_PAGE, "items"),
        MAX_ITEMS_PER_PAGE,
    )
    page_number = _parse_positive_integer(page_number, 1, "page")
    known_statuses = {value for value, _label in ConceptMatchCandidate.STATUS_CHOICES}
    if status and status not in known_statuses:
        raise ConceptMatchRequestError(
            _("Invalid request."),
            _("Unknown candidate status: %(status)s") % {"status": status},
        )

    candidates = run.candidates.all()
    if status:
        candidates = candidates.filter(status=status)

    total_count = candidates.count()
    offset = (page_number - 1) * items_per_page
    page = list(candidates[offset : offset + items_per_page])

    concept_ids = {str(candidate.concept_a_id) for candidate in page} | {
        str(candidate.concept_b_id) for candidate in page
    }
    summaries = _build_concept_summaries(concept_ids, user_is_lingo_admin)

    return {
        "data": [
            {
                "id": candidate.pk,
                "score": candidate.score,
                "signal": candidate.signal,
                "evidence": candidate.evidence,
                "status": candidate.status,
                "concept_a": summaries.get(str(candidate.concept_a_id)),
                "concept_b": summaries.get(str(candidate.concept_b_id)),
                "is_cross_scheme": _is_cross_scheme(candidate, summaries),
            }
            for candidate in page
        ],
        "total_results": total_count,
        "current_page": page_number,
        "items_per_page": items_per_page,
    }


def _is_cross_scheme(candidate, summaries):
    scheme_a = (summaries.get(str(candidate.concept_a_id)) or {}).get("scheme_id")
    scheme_b = (summaries.get(str(candidate.concept_b_id)) or {}).get("scheme_id")
    return bool(scheme_a and scheme_b and scheme_a != scheme_b)


REVIEWABLE_STATUSES = (
    ConceptMatchCandidate.STATUS_PENDING,
    ConceptMatchCandidate.STATUS_DISMISSED,
)


def _require_reviewable_status(status):
    """Linked and merged are recorded by the code that does that work."""
    if status not in REVIEWABLE_STATUSES:
        raise ConceptMatchRequestError(
            _("Invalid request."),
            _("A candidate can only be dismissed or returned to the queue."),
        )


def _dismiss(candidates, user):
    return candidates.filter(status=ConceptMatchCandidate.STATUS_PENDING).update(
        status=ConceptMatchCandidate.STATUS_DISMISSED,
        reviewed_by=user if user is not None and user.is_authenticated else None,
        reviewed_at=timezone.now(),
    )


def _status_change_result(status, updated_count, already_decided_count=0):
    return {
        "updated": updated_count,
        "status": status,
        "skipped": (
            {"already_decided": already_decided_count} if already_decided_count else {}
        ),
    }


def set_candidate_status(run, candidate_ids, status, user):
    _require_reviewable_status(status)
    if status == ConceptMatchCandidate.STATUS_DISMISSED:
        return _status_change_result(
            status, _dismiss(run.candidates.filter(pk__in=candidate_ids), user)
        )
    restored_count, left_dismissed_count = restore_dismissed(
        run, user, candidate_ids=candidate_ids
    )
    return _status_change_result(status, restored_count, left_dismissed_count)


def set_status_for_all(run, status, user):
    _require_reviewable_status(status)
    if status == ConceptMatchCandidate.STATUS_DISMISSED:
        return _status_change_result(status, _dismiss(run.candidates.all(), user))
    restored_count, left_dismissed_count = restore_dismissed(run, user)
    return _status_change_result(status, restored_count, left_dismissed_count)


def _link_outcome(concept_a, concept_b, user_is_lingo_admin):
    """Return (write_to_first, write_to_second, skip_reason) for one pair."""
    if not get_concept_uri(concept_a.pk) or not get_concept_uri(concept_b.pk):
        # An exactMatch names the other concept by URI.
        return None, None, "missing_uri"

    write_to_first = concept_is_writable(concept_a, user_is_lingo_admin)
    write_to_second = concept_is_writable(concept_b, user_is_lingo_admin)
    if not write_to_first and not write_to_second:
        return None, None, "not_editable"

    return write_to_first, write_to_second, None


def link_candidates_with_exact_match(
    run, candidate_ids, user, user_is_lingo_admin=False
):
    """Record a skos:exactMatch for each candidate, skipping unwritable pairs."""
    if len(candidate_ids) > MAX_LINK_BATCH:
        raise ConceptMatchRequestError(
            _("Too many pairs."),
            _("At most %(limit)s pairs can be linked at once.")
            % {"limit": MAX_LINK_BATCH},
        )

    candidates = list(
        run.candidates.filter(
            pk__in=candidate_ids, status=ConceptMatchCandidate.STATUS_PENDING
        )
    )
    concept_ids = {str(candidate.concept_a_id) for candidate in candidates} | {
        str(candidate.concept_b_id) for candidate in candidates
    }
    concepts_by_id = {
        str(concept.pk): concept
        for concept in ResourceInstance.objects.select_related(
            "resource_instance_lifecycle_state"
        ).filter(pk__in=concept_ids)
    }

    edit_transaction_id = uuid.uuid4()
    linked_candidate_ids = []
    linked_pairs = []
    one_way_count = 0
    skipped_by_reason = defaultdict(int)
    already_decided_count = (
        run.candidates.filter(pk__in=candidate_ids)
        .exclude(status=ConceptMatchCandidate.STATUS_PENDING)
        .count()
    )
    if already_decided_count:
        skipped_by_reason["already_decided"] = already_decided_count

    with transaction.atomic():
        for candidate in candidates:
            concept_a = concepts_by_id.get(str(candidate.concept_a_id))
            concept_b = concepts_by_id.get(str(candidate.concept_b_id))
            if concept_a is None or concept_b is None:
                skipped_by_reason["missing_concept"] += 1
                continue

            write_to_first, write_to_second, skip_reason = _link_outcome(
                concept_a, concept_b, user_is_lingo_admin
            )
            if skip_reason:
                skipped_by_reason[skip_reason] += 1
                continue

            write_exact_match_tiles(
                concept_a,
                concept_b,
                edit_transaction_id,
                write_to_first=write_to_first,
                write_to_second=write_to_second,
            )
            if not (write_to_first and write_to_second):
                one_way_count += 1
            linked_candidate_ids.append(candidate.pk)
            linked_pairs.append((candidate.concept_a_id, candidate.concept_b_id))

        if linked_pairs:
            mark_pairs_settled(linked_pairs, ConceptMatchCandidate.STATUS_LINKED, user)

    if linked_candidate_ids:
        index_concepts_in_transaction(edit_transaction_id)

    return {
        "linked": len(linked_candidate_ids),
        "linked_one_way": one_way_count,
        "skipped": dict(skipped_by_reason),
    }


def parse_candidate_ids(body):
    candidate_ids = body.get("candidate_ids")
    if (
        not isinstance(candidate_ids, list)
        or not candidate_ids
        or not all(
            isinstance(candidate_id, int) and not isinstance(candidate_id, bool)
            for candidate_id in candidate_ids
        )
    ):
        raise ConceptMatchRequestError(
            _("Invalid request."), _("candidate_ids must be a list of ids.")
        )
    return candidate_ids


def _parse_uuid_list(values, parameter_name):
    try:
        if not isinstance(values, list):
            raise ValueError
        return [str(uuid.UUID(str(value))) for value in values]
    except ValueError:
        raise ConceptMatchRequestError(
            _("Invalid request."),
            _("%(parameter)s must be a list of ids.") % {"parameter": parameter_name},
        )


def parse_detection_request(body):
    same_language_only = body.get("same_language_only", True)
    if not isinstance(same_language_only, bool):
        raise ConceptMatchRequestError(
            _("Invalid request."), _("same_language_only must be true or false.")
        )

    similarity_threshold = body.get("similarity_threshold")
    if similarity_threshold is None:
        similarity_threshold = DEFAULT_SIMILARITY_THRESHOLD
    elif isinstance(similarity_threshold, bool) or not isinstance(
        similarity_threshold, (int, float)
    ):
        raise ConceptMatchRequestError(
            _("Invalid request."), _("similarity_threshold must be a number.")
        )

    source_concept_set_id = body.get("source_concept_set_id")
    if source_concept_set_id is not None and not isinstance(source_concept_set_id, int):
        raise ConceptMatchRequestError(
            _("Invalid request."), _("source_concept_set_id must be a number.")
        )

    return {
        "scope": MatchScope(
            scheme_ids=_parse_uuid_list(body.get("scheme_ids") or [], "scheme_ids"),
            source_concept_set_id=source_concept_set_id,
            source_concept_ids=_parse_uuid_list(
                body.get("source_concept_ids") or [], "source_concept_ids"
            ),
            cross_scheme_only=bool(body.get("cross_scheme_only")),
        ),
        "signals": tuple(body.get("signals") or EXACT_SIGNALS),
        "same_language_only": same_language_only,
        "similarity_threshold": float(similarity_threshold),
        "name": str(body.get("name") or "").strip()[:255],
    }


def start_detection(
    scope, signals, same_language_only, similarity_threshold, user, name=""
):
    """Queue a run on a worker, returning the pending run to poll."""
    validate_detection_options(signals, similarity_threshold)

    if not worker_is_available():
        raise ConceptMatchRequestError(
            _("Cannot search for matches."),
            _(
                "No background worker answered. One may be busy finishing "
                "another search, in which case this will work again in a "
                "moment. Otherwise no worker is running: start one, or run the "
                "search from the command line with detect_concept_matches."
            ),
            status=HTTPStatus.SERVICE_UNAVAILABLE,
        )

    run = ConceptMatchRun.objects.create(
        user=user if user is not None and user.is_authenticated else None,
        name=name,
        status=ConceptMatchRun.STATUS_PENDING,
        parameters={
            **scope.as_parameters(),
            "signals": list(signals),
            "same_language_only": same_language_only,
            "similarity_threshold": similarity_threshold,
        },
    )
    detect_concept_matches_task.apply_async(
        args=[
            run.pk,
            scope.as_parameters(),
            list(signals),
            {
                "same_language_only": same_language_only,
                "similarity_threshold": similarity_threshold,
            },
        ],
        **({"queue": MATCH_TASK_QUEUE} if MATCH_TASK_QUEUE else {}),
    )
    return run
