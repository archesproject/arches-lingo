"""Editors' decisions about pairs, shared by every run that found them.

A candidate's review status is its pair's decision, or pending when there is none.
"""

from django.db import connection
from django.db.models import Exists, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from arches_lingo.models import ConceptMatchCandidate, ConceptPairDecision
from arches_lingo.utils.concept_matching import decided_pairs_sql

STATUS_PENDING = ConceptMatchCandidate.STATUS_PENDING
STATUS_DISMISSED = ConceptMatchCandidate.STATUS_DISMISSED
STATUS_LINKED = ConceptMatchCandidate.STATUS_LINKED
STATUS_MERGED = ConceptMatchCandidate.STATUS_MERGED

STATUS_RANKS = {STATUS_DISMISSED: 1, STATUS_LINKED: 2, STATUS_MERGED: 3}


def _decided_by(user):
    return user if user is not None and user.is_authenticated else None


def _decisions_for_candidate():
    return ConceptPairDecision.objects.filter(
        concept_a_id=OuterRef("concept_a_id"), concept_b_id=OuterRef("concept_b_id")
    )


def with_review_status(candidates):
    return candidates.annotate(
        review_status=Coalesce(
            Subquery(_decisions_for_candidate().values("status")[:1]),
            Value(STATUS_PENDING),
        )
    )


def filter_by_review_status(candidates, status):
    if status == STATUS_PENDING:
        return candidates.filter(~Exists(_decisions_for_candidate()))
    return candidates.filter(Exists(_decisions_for_candidate().filter(status=status)))


def count_by_review_status(run_ids):
    """Return {run id: {status: count}}, with every status present."""
    counts_by_run_id = {
        run_id: {status: 0 for status, _label in ConceptMatchCandidate.STATUS_CHOICES}
        for run_id in run_ids
    }
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT candidate.run_id,
                   coalesce(decision.status, %(pending_status)s),
                   count(*)
              FROM {ConceptMatchCandidate._meta.db_table} candidate
              LEFT JOIN {ConceptPairDecision._meta.db_table} decision
                ON decision.concept_a_id = candidate.concept_a_id
               AND decision.concept_b_id = candidate.concept_b_id
             WHERE candidate.run_id = ANY(%(run_ids)s)
             GROUP BY 1, 2
            """,
            {"pending_status": STATUS_PENDING, "run_ids": list(run_ids)},
        )
        for run_id, status, count in cursor.fetchall():
            counts_by_run_id[run_id][status] = count
    return counts_by_run_id


def _candidate_clause(candidate_ids, params):
    if candidate_ids is None:
        return ""
    params["candidate_ids"] = list(candidate_ids)
    return " AND candidate.id = ANY(%(candidate_ids)s)"


def dismiss(run, user=None, candidate_ids=None):
    """Dismiss the run's pending pairs, or those among `candidate_ids`;
    return how many."""
    params = {
        "run_id": run.pk,
        "dismissed_status": STATUS_DISMISSED,
        "decided_by_id": getattr(_decided_by(user), "pk", None),
        "decided_at": timezone.now(),
    }
    candidate_clause = _candidate_clause(candidate_ids, params)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO {ConceptPairDecision._meta.db_table}
                   (concept_a_id, concept_b_id, status, decided_by_id, decided_at)
            SELECT candidate.concept_a_id, candidate.concept_b_id,
                   %(dismissed_status)s, %(decided_by_id)s, %(decided_at)s
              FROM {ConceptMatchCandidate._meta.db_table} candidate
             WHERE candidate.run_id = %(run_id)s{candidate_clause}
            ON CONFLICT (concept_a_id, concept_b_id) DO NOTHING
            """,
            params,
        )
        return cursor.rowcount


def restore_dismissed(run, candidate_ids=None):
    """Return dismissed pairs to the queue, returning (restored, left dismissed).

    A pair linked or merged outside match review since it was dismissed stays
    dismissed.
    """
    decided_sql, decided_params = decided_pairs_sql()
    params = {
        **decided_params,
        "run_id": run.pk,
        "dismissed_status": STATUS_DISMISSED,
    }
    candidate_clause = _candidate_clause(candidate_ids, params)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            DELETE FROM {ConceptPairDecision._meta.db_table} decision
             USING {ConceptMatchCandidate._meta.db_table} candidate
             WHERE candidate.run_id = %(run_id)s{candidate_clause}
               AND decision.concept_a_id = candidate.concept_a_id
               AND decision.concept_b_id = candidate.concept_b_id
               AND decision.status = %(dismissed_status)s
               AND NOT EXISTS (
                   SELECT 1
                     FROM ({decided_sql}) decided
                    WHERE decided.concept_a = decision.concept_a_id::text
                      AND decided.concept_b = decision.concept_b_id::text
               )
            """,
            params,
        )
        restored_count = cursor.rowcount

    selected_candidates = run.candidates.all()
    if candidate_ids is not None:
        selected_candidates = selected_candidates.filter(pk__in=candidate_ids)
    left_dismissed_count = filter_by_review_status(
        selected_candidates, STATUS_DISMISSED
    ).count()
    return restored_count, left_dismissed_count


def mark_pairs_settled(pairs, status, user=None):
    """Record a link or merge for these pairs; a link outranks a dismissal, and
    only a merge outranks a link. Returns how many decisions changed."""
    canonical_pairs = {
        ConceptMatchCandidate.order_concept_ids(first_id, second_id)
        for first_id, second_id in pairs
    }
    if not canonical_pairs:
        return 0

    matching_pairs = Q()
    for concept_a_id, concept_b_id in canonical_pairs:
        matching_pairs |= Q(concept_a_id=concept_a_id, concept_b_id=concept_b_id)
    decisions_by_pair = {
        (str(decision.concept_a_id), str(decision.concept_b_id)): decision
        for decision in ConceptPairDecision.objects.filter(matching_pairs)
    }

    decided_by = _decided_by(user)
    decided_at = timezone.now()
    new_decisions = []
    raised_decisions = []
    for concept_a_id, concept_b_id in canonical_pairs:
        decision = decisions_by_pair.get((concept_a_id, concept_b_id))
        if decision is None:
            new_decisions.append(
                ConceptPairDecision(
                    concept_a_id=concept_a_id,
                    concept_b_id=concept_b_id,
                    status=status,
                    decided_by=decided_by,
                    decided_at=decided_at,
                )
            )
        elif STATUS_RANKS[status] > STATUS_RANKS[decision.status]:
            decision.status = status
            decision.decided_by = decided_by
            decision.decided_at = decided_at
            raised_decisions.append(decision)

    ConceptPairDecision.objects.bulk_create(new_decisions)
    ConceptPairDecision.objects.bulk_update(
        raised_decisions, ["status", "decided_by", "decided_at"]
    )
    return len(new_decisions) + len(raised_decisions)


def hand_pending_pairs_to_survivor(absorbed_concept_id, survivor_concept_id):
    """Re-point a retired or deleted concept's pending pairs at its survivor,
    dropping any the run already holds for the survivor.

    Decided pairs keep the absorbed concept, so a dismissal is never carried
    over: the survivor has gained the absorbed concept's values.
    """
    absorbed_concept_id = str(absorbed_concept_id)
    survivor_concept_id = str(survivor_concept_id)
    pending_with_absorbed = filter_by_review_status(
        ConceptMatchCandidate.objects.filter(
            Q(concept_a_id=absorbed_concept_id) | Q(concept_b_id=absorbed_concept_id)
        ),
        STATUS_PENDING,
    )
    for candidate in pending_with_absorbed:
        other_concept_id = (
            str(candidate.concept_b_id)
            if str(candidate.concept_a_id) == absorbed_concept_id
            else str(candidate.concept_a_id)
        )
        concept_a_id, concept_b_id = ConceptMatchCandidate.order_concept_ids(
            survivor_concept_id, other_concept_id
        )
        already_in_run = ConceptMatchCandidate.objects.filter(
            run_id=candidate.run_id,
            concept_a_id=concept_a_id,
            concept_b_id=concept_b_id,
        ).exists()
        if already_in_run:
            candidate.delete()
            continue
        candidate.concept_a_id = concept_a_id
        candidate.concept_b_id = concept_b_id
        candidate.save(update_fields=["concept_a_id", "concept_b_id"])
