"""A candidate's review status, read from the vocabulary rather than stored.

Merged comes from ``ConceptMerge``, linked from a match tile (any relation) on
either concept pointing at the other, dismissed from ``ConceptPairDismissal``;
anything else is pending. So deleting the match tile in the concept editor
reopens the pair everywhere.
"""

from django.db import connection
from django.db.models import Q
from django.db.models.expressions import RawSQL
from django.utils import timezone

from arches_lingo.const import (
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_NODEGROUP,
    MATCH_STATUS_COMPARATE_NODE,
    MATCH_STATUS_NODEGROUP,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)
from arches_lingo.models import (
    ConceptMatchCandidate,
    ConceptMerge,
    ConceptPairDismissal,
)

STATUS_PENDING = ConceptMatchCandidate.STATUS_PENDING
STATUS_DISMISSED = ConceptMatchCandidate.STATUS_DISMISSED
STATUS_LINKED = ConceptMatchCandidate.STATUS_LINKED
STATUS_MERGED = ConceptMatchCandidate.STATUS_MERGED

CANDIDATE_TABLE = ConceptMatchCandidate._meta.db_table


def _review_status_sql():
    """Return (sql, params) computing the status of the candidate row in scope.

    Each check is an index probe per candidate, on `(nodegroupid,
    resourceinstanceid)` for tiles, rather than a join over every match tile.
    """
    sql = f"""
        CASE
          WHEN EXISTS (
                 SELECT 1
                   FROM {ConceptMerge._meta.db_table} merge
                  WHERE (merge.survivor_concept_id = {CANDIDATE_TABLE}.concept_a_id
                         AND merge.absorbed_concept_id = {CANDIDATE_TABLE}.concept_b_id)
                     OR (merge.survivor_concept_id = {CANDIDATE_TABLE}.concept_b_id
                         AND merge.absorbed_concept_id = {CANDIDATE_TABLE}.concept_a_id)
               ) THEN %s
          WHEN EXISTS (
                 SELECT 1
                   FROM tiles match_tile
                   JOIN tiles uri_tile
                     ON uri_tile.nodegroupid = '{URI_NODEGROUP}'
                    AND uri_tile.resourceinstanceid = CASE
                            WHEN match_tile.resourceinstanceid = {CANDIDATE_TABLE}.concept_a_id
                            THEN {CANDIDATE_TABLE}.concept_b_id
                            ELSE {CANDIDATE_TABLE}.concept_a_id
                        END
                    AND lower(btrim(uri_tile.tiledata ->> '{URI_CONTENT_NODE}'))
                        = lower(btrim(match_tile.tiledata ->> '{MATCH_STATUS_COMPARATE_NODE}'))
                  WHERE match_tile.nodegroupid = '{MATCH_STATUS_NODEGROUP}'
                    AND match_tile.resourceinstanceid IN (
                            {CANDIDATE_TABLE}.concept_a_id, {CANDIDATE_TABLE}.concept_b_id
                        )
               ) THEN %s
          WHEN EXISTS (
                 SELECT 1
                   FROM {ConceptPairDismissal._meta.db_table} dismissal
                  WHERE dismissal.concept_a_id = {CANDIDATE_TABLE}.concept_a_id
                    AND dismissal.concept_b_id = {CANDIDATE_TABLE}.concept_b_id
               ) THEN %s
          ELSE %s
        END
    """
    params = [
        STATUS_MERGED,
        STATUS_LINKED,
        STATUS_DISMISSED,
        STATUS_PENDING,
    ]
    return sql, params


def _label_search_sql(search):
    """Return (sql, params) true when either concept has a label containing
    `search`, ignoring case."""
    escaped_search = (
        search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    sql = f"""
        EXISTS (
            SELECT 1
              FROM tiles label_tile
             WHERE label_tile.nodegroupid = '{CONCEPT_NAME_NODEGROUP}'
               AND label_tile.resourceinstanceid IN (
                       {CANDIDATE_TABLE}.concept_a_id, {CANDIDATE_TABLE}.concept_b_id
                   )
               AND label_tile.tiledata ->> '{CONCEPT_NAME_CONTENT_NODE}' ILIKE %s
        )
    """
    return sql, [f"%{escaped_search}%"]


def filter_by_label_search(candidates, search):
    if not search:
        return candidates
    search_sql, search_params = _label_search_sql(search)
    return candidates.annotate(matches_search=RawSQL(search_sql, search_params)).filter(
        matches_search=True
    )


def with_review_status(candidates):
    status_sql, status_params = _review_status_sql()
    return candidates.annotate(review_status=RawSQL(status_sql, status_params))


def filter_by_review_status(candidates, status):
    return with_review_status(candidates).filter(review_status=status)


def count_by_review_status(run_ids):
    """Return {run id: {status: count}}, with every status present."""
    counts_by_run_id = {
        run_id: {status: 0 for status, _label in ConceptMatchCandidate.STATUS_CHOICES}
        for run_id in run_ids
    }
    status_sql, status_params = _review_status_sql()
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT run_id, review_status, count(*)
              FROM (
                  SELECT {CANDIDATE_TABLE}.run_id, {status_sql} AS review_status
                    FROM {CANDIDATE_TABLE}
                   WHERE {CANDIDATE_TABLE}.run_id = ANY(%s)
              ) candidate_status
             GROUP BY 1, 2
            """,
            [*status_params, list(run_ids)],
        )
        for run_id, status, count in cursor.fetchall():
            counts_by_run_id[run_id][status] = count
    return counts_by_run_id


def _selected_candidates_sql(run, candidate_ids, search):
    sql = f"{CANDIDATE_TABLE}.run_id = %s"
    params = [run.pk]
    if candidate_ids is not None:
        sql += f" AND {CANDIDATE_TABLE}.id = ANY(%s)"
        params.append(list(candidate_ids))
    if search:
        search_sql, search_params = _label_search_sql(search)
        sql += f" AND {search_sql}"
        params.extend(search_params)
    return sql, params


def dismiss(run, user=None, candidate_ids=None, search=None):
    """Dismiss the run's pending pairs, narrowed to `candidate_ids` or to pairs
    matching `search`; return how many."""
    selected_sql, selected_params = _selected_candidates_sql(run, candidate_ids, search)
    status_sql, status_params = _review_status_sql()
    dismissed_by = user if user is not None and user.is_authenticated else None
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO {ConceptPairDismissal._meta.db_table}
                   (concept_a_id, concept_b_id, dismissed_by_id, dismissed_at)
            SELECT {CANDIDATE_TABLE}.concept_a_id, {CANDIDATE_TABLE}.concept_b_id,
                   %s, %s
              FROM {CANDIDATE_TABLE}
             WHERE {selected_sql}
               AND {status_sql} = %s
            ON CONFLICT (concept_a_id, concept_b_id) DO NOTHING
            """,
            [
                getattr(dismissed_by, "pk", None),
                timezone.now(),
                *selected_params,
                *status_params,
                STATUS_PENDING,
            ],
        )
        return cursor.rowcount


def restore_dismissed(run, candidate_ids=None, search=None):
    """Return dismissed pairs to the queue, returning (restored, not restorable).

    A pair linked or merged since it was dismissed shows as linked or merged, so
    it is not restored; its dismissal stays underneath in case the link goes.
    """
    selected_sql, selected_params = _selected_candidates_sql(run, candidate_ids, search)
    status_sql, status_params = _review_status_sql()
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            DELETE FROM {ConceptPairDismissal._meta.db_table} restored
             USING {CANDIDATE_TABLE}
             WHERE {selected_sql}
               AND restored.concept_a_id = {CANDIDATE_TABLE}.concept_a_id
               AND restored.concept_b_id = {CANDIDATE_TABLE}.concept_b_id
               AND {status_sql} = %s
            """,
            [*selected_params, *status_params, STATUS_DISMISSED],
        )
        restored_count = cursor.rowcount

    if candidate_ids is None:
        return restored_count, 0
    selected_count = run.candidates.filter(pk__in=candidate_ids).count()
    return restored_count, selected_count - restored_count


def hand_pending_pairs_to_survivor(absorbed_concept_id, survivor_concept_id):
    """Re-point a retired or deleted concept's pending pairs at its survivor,
    dropping any the run already holds for the survivor.

    Dismissed pairs keep the absorbed concept, so a dismissal is never carried
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
