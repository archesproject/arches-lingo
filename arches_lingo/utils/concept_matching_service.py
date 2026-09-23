"""Turn stored match runs and candidates into what the review interface needs.

Detection stores pairs of concept ids. Reviewing them needs names, and the
scheme each concept sits in -- a pair is read very differently depending on
whether it spans two vocabularies or duplicates something inside one. Both are
gathered per page of candidates rather than per candidate, so a page of fifty
pairs costs the same handful of queries as a page of one.
"""

import datetime
import uuid
from collections import defaultdict
from http import HTTPStatus

from django.conf import settings
from django.db import transaction
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
    ALL_SIGNALS,
    SIGNAL_TRIGRAM,
    count_labels_by_scheme,
    get_scheme_ids_for_concepts,
    mark_pairs_settled,
    run_detection,
)
from arches_lingo.utils.concept_merge import (
    concept_is_writable,
    get_concept_uri,
    write_exact_match_tiles,
)

DEFAULT_ITEMS_PER_PAGE = 50
MAX_ITEMS_PER_PAGE = 200

# Linking writes up to two tiles per pair through the full tile save path, so a
# request is capped at a size that stays comfortably inside one. Reviewers page
# through the queue anyway.
MAX_LINK_BATCH = 200

# How long a run may go without reporting progress before it is presumed dead.
# The detection loop stores what it has found every ten seconds, but a single
# slice of a large vocabulary can run considerably longer than that, so the
# threshold is well clear of any honest gap between heartbeats.
STALE_RUN_SECONDS = getattr(settings, "LINGO_MATCH_STALE_SECONDS", 300)


class ConceptMatchRequestError(Exception):
    """A request the review interface cannot be given what it asked for."""

    def __init__(self, title, message, status=HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.title = title
        self.message = message
        self.status = status


def serialize_run(run):
    # Elapsed time is measured here rather than from the timestamps, because the
    # client cannot subtract them: with USE_TZ off these are naive timestamps in
    # the server's own zone, which a browser in another zone reads as its local
    # time and places in the future. Both ends of this subtraction come from one
    # clock, so the answer holds whatever zone either side is in.
    ended_at = run.finished or timezone.now()

    counts_by_status = {
        status: 0 for status, _label in ConceptMatchCandidate.STATUS_CHOICES
    }
    for row in run.candidates.values("status").annotate(count=Count("status")):
        counts_by_status[row["status"]] = row["count"]

    return {
        "id": run.pk,
        "name": run.name,
        "status": run.status,
        "created": run.created.isoformat(),
        "finished": run.finished.isoformat() if run.finished else None,
        "elapsed_seconds": max(0, int((ended_at - run.created).total_seconds())),
        "parameters": run.parameters,
        "candidate_count": run.candidate_count,
        "error_message": run.error_message,
        # Every status, not just the outstanding one: a reviewer wants to see
        # what they linked and merged as much as what is left to decide, and
        # one grouped count costs what counting the pending ones alone did.
        "counts_by_status": counts_by_status,
        "pending_count": counts_by_status[ConceptMatchCandidate.STATUS_PENDING],
    }


def serialize_scope_sizes():
    """How many labels a run would compare, in all and per scheme."""
    total_labels, labels_by_scheme = count_labels_by_scheme()
    return {
        "total_labels": total_labels,
        "labels_by_scheme": labels_by_scheme,
    }


def worker_is_available():
    """Whether a background worker would pick up a run queued now.

    A worker running under the solo pool executes tasks in the same process that
    answers control commands, so while it is working it cannot answer a ping and
    is indistinguishable from a worker that is not there at all. Refusing on that
    basis would mean no search could be started while another was running.

    A run that is still reporting progress is the better evidence, and it is the
    same threshold ``reap_stale_runs`` uses to decide that a run has stopped: a
    worker whose progress counts as alive there counts as alive here.
    """
    if task_management.check_if_celery_available():
        return True

    cutoff = timezone.now() - datetime.timedelta(seconds=STALE_RUN_SECONDS)
    return ConceptMatchRun.objects.filter(
        status=ConceptMatchRun.STATUS_RUNNING, last_progress__gte=cutoff
    ).exists()


def reap_stale_runs():
    """Fail runs that stopped reporting, returning how many were closed out.

    A worker restarted mid-run cannot fail its own run: celery acknowledges a
    task when it receives it, so the message dies with the worker and nothing is
    left to notice. The row would otherwise claim to be running forever, and the
    interface would poll a run that no process is working on.

    Runs predating the heartbeat fall back to when they were created, which is
    the most recent moment they are known to have been alive.
    """
    cutoff = timezone.now() - datetime.timedelta(seconds=STALE_RUN_SECONDS)
    return ConceptMatchRun.objects.filter(
        Q(last_progress__lt=cutoff) | Q(last_progress__isnull=True, created__lt=cutoff),
        status__in=[ConceptMatchRun.STATUS_PENDING, ConceptMatchRun.STATUS_RUNNING],
    ).update(
        status=ConceptMatchRun.STATUS_FAILED,
        finished=timezone.now(),
        error_message=_(
            "This run stopped reporting progress and was presumed interrupted. "
            "The server may have been restarted while it was working."
        ),
    )


# Why a concept cannot be merged into. The two have different remedies -- one is
# the concept's own lifecycle state, the other its scheme's -- so they are
# reported apart rather than as a bare "no".
CANNOT_RECEIVE_NOT_EDITABLE = "not_editable"
CANNOT_RECEIVE_SCHEME_LOCKED = "scheme_locked"


def _reasons_concepts_cannot_receive_data(
    concept_ids, scheme_ids_by_concept_id, user_is_lingo_admin
):
    """Why each concept could not be merged into; absent means it could be.

    The same rule as ``concept_is_writable``, asked of a whole page at once: a
    page of fifty pairs names a hundred concepts, and deciding this one concept
    at a time would be a hundred round trips.
    """
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

    Labels rather than the resource descriptor, so the client can pick the best
    one for the reader's language the way every other concept name is chosen.
    """
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
            # A merge writes to one side only, so this is what decides which way
            # round a pair may be merged -- the other side is only read from.
            "can_receive_data": concept_id not in cannot_receive_reasons,
            "cannot_receive_reason": cannot_receive_reasons.get(concept_id),
        }
    return summaries


def serialize_candidate_page(
    run, status=None, page_number=1, items_per_page=None, user_is_lingo_admin=False
):
    """Return one page of a run's candidates, with both concepts named."""
    items_per_page = min(
        int(items_per_page or DEFAULT_ITEMS_PER_PAGE), MAX_ITEMS_PER_PAGE
    )
    page_number = max(int(page_number or 1), 1)

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


def set_candidate_status(run, candidate_ids, status, user):
    """Record a review decision against candidates of this run.

    Only the decisions a reviewer makes by hand are settable here: linking and
    merging are consequences of doing the work, and are recorded by the code
    that does it.
    """
    reviewable_statuses = {
        ConceptMatchCandidate.STATUS_PENDING,
        ConceptMatchCandidate.STATUS_DISMISSED,
    }
    if status not in reviewable_statuses:
        raise ConceptMatchRequestError(
            _("Invalid request."),
            _("A candidate can only be dismissed or returned to the queue."),
        )

    candidates = run.candidates.filter(pk__in=candidate_ids)
    updated_count = candidates.update(
        status=status,
        reviewed_by=user if user is not None and user.is_authenticated else None,
        reviewed_at=timezone.now(),
    )
    return {"updated": updated_count, "status": status}


def dismiss_all_pending(run, user):
    """Dismiss every pair of this run still awaiting a decision.

    A corpus-wide fuzzy run can suggest tens of thousands of pairs, far more
    than a reviewer can name one at a time, so clearing the rest of the queue is
    done by the server rather than by sending back every id.
    """
    updated_count = run.candidates.filter(
        status=ConceptMatchCandidate.STATUS_PENDING
    ).update(
        status=ConceptMatchCandidate.STATUS_DISMISSED,
        reviewed_by=user if user is not None and user.is_authenticated else None,
        reviewed_at=timezone.now(),
    )
    return {
        "updated": updated_count,
        "status": ConceptMatchCandidate.STATUS_DISMISSED,
    }


def _link_outcome(concept_a, concept_b, user_is_lingo_admin):
    """Decide what can be written for one pair, and why not when it cannot."""
    if not get_concept_uri(concept_a.pk) or not get_concept_uri(concept_b.pk):
        # An exactMatch names the other concept by URI, so a concept without
        # one cannot be pointed at or point anywhere.
        return None, None, "missing_uri"

    write_to_first = concept_is_writable(concept_a, user_is_lingo_admin)
    write_to_second = concept_is_writable(concept_b, user_is_lingo_admin)
    if not write_to_first and not write_to_second:
        return None, None, "not_editable"

    return write_to_first, write_to_second, None


def link_candidates_with_exact_match(
    run, candidate_ids, user, user_is_lingo_admin=False
):
    """Record a skos:exactMatch between the concepts of each candidate.

    Linking says the two concepts mean the same thing while leaving both in
    place, which is the right outcome for a pair spanning two vocabularies:
    neither scheme loses a concept, and each record points at the other.

    A pair is skipped rather than failed when it cannot be written -- one of the
    concepts has no URI, or neither side may be edited -- so one awkward pair in
    a selection of fifty does not cost the other forty-nine.
    """
    if len(candidate_ids) > MAX_LINK_BATCH:
        raise ConceptMatchRequestError(
            _("Too many pairs."),
            _("At most %(limit)s pairs can be linked at once.")
            % {"limit": MAX_LINK_BATCH},
        )

    candidates = list(run.candidates.filter(pk__in=candidate_ids))
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

    with transaction.atomic():
        for candidate in candidates:
            concept_a = concepts_by_id.get(str(candidate.concept_a_id))
            concept_b = concepts_by_id.get(str(candidate.concept_b_id))
            if concept_a is None or concept_b is None:
                # The concept was deleted after the run that suggested it.
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
            # Settled wherever the pair is queued, not only in the run being
            # reviewed: the same two concepts can be suggested by several runs.
            mark_pairs_settled(linked_pairs, ConceptMatchCandidate.STATUS_LINKED, user)

    # One bulk pass once every tile is written, rather than a round trip per
    # tile inside the loop above.
    if linked_candidate_ids:
        index_concepts_in_transaction(edit_transaction_id)

    return {
        "linked": len(linked_candidate_ids),
        "linked_one_way": one_way_count,
        "skipped": dict(skipped_by_reason),
    }


def start_detection(
    scope, signals, same_language_only, similarity_threshold, user, name=""
):
    """Begin a run, in the foreground or on a worker depending on the signals.

    The exact signals finish in seconds and are answered inside the request, so
    the interface can show results immediately. The fuzzy signal compares every
    label against every other and takes minutes at vocabulary scale, so it is
    handed to a worker and the caller polls the run it gets back.
    """
    unknown_signals = set(signals) - set(ALL_SIGNALS)
    if unknown_signals:
        raise ConceptMatchRequestError(
            _("Invalid request."),
            _("Unsupported signal(s): %(signals)s")
            % {"signals": ", ".join(sorted(unknown_signals))},
        )

    if SIGNAL_TRIGRAM not in signals:
        return run_detection(
            scope,
            signals=tuple(signals),
            same_language_only=same_language_only,
            similarity_threshold=similarity_threshold,
            user=user,
            log=lambda message: None,
            name=name,
        )

    if not worker_is_available():
        raise ConceptMatchRequestError(
            _("Cannot search for similar labels."),
            _(
                "No background worker answered. One may be busy finishing "
                "another search, in which case this will work again in a "
                "moment. Otherwise no worker is running: the exact signals work "
                "without one, or a vocabulary-wide search can be started with "
                "the detect_concept_matches command."
            ),
            status=HTTPStatus.SERVICE_UNAVAILABLE,
        )

    # The run is created here rather than in the task so the response carries
    # something the interface can poll straight away.
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
        ]
    )
    return run
