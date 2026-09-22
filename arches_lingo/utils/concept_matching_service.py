"""Turn stored match runs and candidates into what the review interface needs.

Detection stores pairs of concept ids. Reviewing them needs names, and the
scheme each concept sits in -- a pair is read very differently depending on
whether it spans two vocabularies or duplicates something inside one. Both are
gathered per page of candidates rather than per candidate, so a page of fifty
pairs costs the same handful of queries as a page of one.
"""

import uuid
from collections import defaultdict
from http import HTTPStatus

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from arches.app.models.models import ResourceInstance

import arches.app.utils.task_management as task_management

from arches_lingo.models import ConceptMatchCandidate, ConceptMatchRun
from arches_lingo.tasks import detect_concept_matches_task
from arches_lingo.utils.concept_builder import ConceptBuilder
from arches_lingo.utils.concept_lifecycle import index_concepts_in_transaction
from arches_lingo.utils.concept_matching import (
    ALL_SIGNALS,
    SIGNAL_TRIGRAM,
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


class ConceptMatchRequestError(Exception):
    """A request the review interface cannot be given what it asked for."""

    def __init__(self, title, message, status=HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.title = title
        self.message = message
        self.status = status


def serialize_run(run):
    return {
        "id": run.pk,
        "status": run.status,
        "created": run.created.isoformat(),
        "finished": run.finished.isoformat() if run.finished else None,
        "parameters": run.parameters,
        "candidate_count": run.candidate_count,
        "error_message": run.error_message,
        "pending_count": run.candidates.filter(
            status=ConceptMatchCandidate.STATUS_PENDING
        ).count(),
    }


def _build_concept_summaries(concept_ids):
    """Return {concept id: {labels, scheme}} for naming a page of pairs.

    Labels rather than the resource descriptor, so the client can pick the best
    one for the reader's language the way every other concept name is chosen.
    """
    if not concept_ids:
        return {}

    builder = ConceptBuilder(list(concept_ids))
    scheme_ids_by_concept_id = get_scheme_ids_for_concepts(concept_ids)

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
        }
    return summaries


def serialize_candidate_page(run, status=None, page_number=1, items_per_page=None):
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
    summaries = _build_concept_summaries(concept_ids)

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


def start_detection(scope, signals, same_language_only, similarity_threshold, user):
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
        )

    if not task_management.check_if_celery_available():
        raise ConceptMatchRequestError(
            _("Cannot search for similar labels."),
            _(
                "Comparing similar labels needs a background worker, which is "
                "not running. The exact signals work without one, or a "
                "vocabulary-wide search can be started with the "
                "detect_concept_matches command."
            ),
            status=HTTPStatus.SERVICE_UNAVAILABLE,
        )

    # The run is created here rather than in the task so the response carries
    # something the interface can poll straight away.
    run = ConceptMatchRun.objects.create(
        user=user if user is not None and user.is_authenticated else None,
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
