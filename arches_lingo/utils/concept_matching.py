"""Find concepts that probably mean the same thing.

Detection produces *pairs*: two concepts and the reason they were suggested. A
pair is a suggestion, not a decision, so the candidates it writes carry a review
state and the pairs an editor has already settled -- by linking them with an
exactMatch, or by merging one into the other -- are never suggested again.

Signals are independent and can be run in any combination. Two are implemented
here, both exact and both cheap enough to run inside a request:

  * `shared_identifier` -- the concepts carry the same identifier or URI
  * `exact_label` -- a label on one matches a label on the other exactly

The fuzzy signal that `pg_trgm` supports is deliberately absent; see
docs/concept-match-detection-plan.md for why it waits.

Everything is expressed as SQL over `tiles` rather than through the ORM: the
label corpus runs to hundreds of thousands of rows, and the trigram index the
fuzzy signal will need is defined on the raw `tiledata ->> node_id` expression.
"""

import json

from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from arches_lingo.const import (
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPTS_GRAPH_ID,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    IDENTIFIER_CONTENT_NODE,
    IDENTIFIER_NODEGROUP,
    MATCH_STATUS_COMPARATE_NODE,
    MATCH_STATUS_NODEGROUP,
    TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)
from arches_lingo.models import (
    ConceptMatchCandidate,
    ConceptMatchRun,
    ConceptMerge,
    ConceptSetMember,
)

SIGNAL_SHARED_IDENTIFIER = ConceptMatchCandidate.SIGNAL_SHARED_IDENTIFIER
SIGNAL_EXACT_LABEL = ConceptMatchCandidate.SIGNAL_EXACT_LABEL

EXACT_SIGNALS = (SIGNAL_SHARED_IDENTIFIER, SIGNAL_EXACT_LABEL)

CANDIDATE_BATCH_SIZE = 2_000


class ConceptMatchError(Exception):
    """A run that cannot proceed as asked."""


class MatchScope:
    """Which concepts a run compares, and which it compares them against.

    `source` is the side being reviewed; `target` is what it is held up against.
    Leaving both unset compares every concept with every other, which is what a
    whole-corpus duplicate sweep is.
    """

    def __init__(
        self,
        source_scheme_id=None,
        target_scheme_id=None,
        source_concept_set_id=None,
        source_concept_ids=None,
        cross_scheme_only=False,
    ):
        self.source_scheme_id = source_scheme_id
        self.target_scheme_id = target_scheme_id
        self.source_concept_set_id = source_concept_set_id
        self.source_concept_ids = [
            str(concept_id) for concept_id in source_concept_ids or []
        ]
        self.cross_scheme_only = cross_scheme_only

    def as_parameters(self):
        return {
            "source_scheme_id": self.source_scheme_id,
            "target_scheme_id": self.target_scheme_id,
            "source_concept_set_id": self.source_concept_set_id,
            "source_concept_ids": self.source_concept_ids,
            "cross_scheme_only": self.cross_scheme_only,
        }

    def resolve_source_concept_ids(self):
        """Explicit source ids, or None when the source is not an id list.

        A concept set is resolved to its members here so the rest of the engine
        only ever deals with one kind of narrowing.
        """
        if self.source_concept_ids:
            return self.source_concept_ids

        if self.source_concept_set_id is not None:
            member_ids = ConceptSetMember.objects.filter(
                concept_set_id=self.source_concept_set_id
            ).values_list("concept_id", flat=True)
            return [str(member_id) for member_id in member_ids]

        return None


# A concept's scheme comes from part_of_scheme, or from top_concept_of when it
# sits at the top of one. Both are read so scoping a run to a scheme does not
# silently omit its facets.
_CONCEPT_SCHEME_SQL = f"""
    SELECT DISTINCT ON (concept_id) concept_id, scheme_id
      FROM (
          SELECT resourceinstanceid AS concept_id,
                 (tiledata -> '{CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}'
                     -> 0 ->> 'resourceId')::uuid AS scheme_id,
                 0 AS priority
            FROM tiles
           WHERE nodegroupid = '{CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}'
          UNION ALL
          SELECT resourceinstanceid,
                 (tiledata -> '{TOP_CONCEPT_OF_NODE_AND_NODEGROUP}'
                     -> 0 ->> 'resourceId')::uuid,
                 1
            FROM tiles
           WHERE nodegroupid = '{TOP_CONCEPT_OF_NODE_AND_NODEGROUP}'
      ) scheme_of_concept
     WHERE scheme_id IS NOT NULL
     ORDER BY concept_id, priority
"""

# Labels, normalized for comparison. Case and surrounding whitespace are not a
# meaningful difference between two concept names.
_LABEL_SQL = f"""
    SELECT resourceinstanceid AS concept_id,
           lower(btrim(tiledata ->> '{CONCEPT_NAME_CONTENT_NODE}')) AS content,
           tiledata ->> '{CONCEPT_NAME_LANGUAGE_NODE}' AS language
      FROM tiles
     WHERE nodegroupid = '{CONCEPT_NAME_NODEGROUP}'
       AND btrim(coalesce(tiledata ->> '{CONCEPT_NAME_CONTENT_NODE}', '')) <> ''
"""

# URIs are globally meaningful, so two concepts carrying the same one are almost
# certainly the same concept. Bare identifiers are deliberately not compared:
# they are allocated per scheme by ConceptIdentifierCounter and are short
# numbers, so equality between schemes says nothing.
_URI_SQL = f"""
    SELECT resourceinstanceid AS concept_id,
           lower(btrim(tiledata ->> '{URI_CONTENT_NODE}')) AS uri
      FROM tiles
     WHERE nodegroupid = '{URI_NODEGROUP}'
       AND btrim(coalesce(tiledata ->> '{URI_CONTENT_NODE}', '')) <> ''
"""


def get_scheme_ids_for_concepts(concept_ids):
    """Return {concept id: scheme id} for the concepts given.

    Public because reviewing a pair needs the same answer detection does: a pair
    reads very differently depending on whether it spans two vocabularies.
    """
    if not concept_ids:
        return {}

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT concept_id, scheme_id
              FROM ({_CONCEPT_SCHEME_SQL}) concept_scheme
             WHERE concept_id = ANY(%(concept_ids)s::uuid[])
            """,
            {"concept_ids": [str(concept_id) for concept_id in concept_ids]},
        )
        return {
            str(concept_id): str(scheme_id)
            for concept_id, scheme_id in cursor.fetchall()
        }


def _scope_clauses(scope, source_concept_ids):
    """Return (sql, params) narrowing which pairs a run keeps.

    A pair has no inherent direction -- it is stored lowest id first, not source
    first -- so every narrowing asks whether *either* side qualifies rather than
    pinning one side to the source.

    `source_concept_ids` is None when the signal has already restricted one side
    to them, which it does whenever it can: filtering a whole self-join after the
    fact costs the same as not scoping at all.
    """
    clauses = []
    params = {}

    if source_concept_ids is not None:
        clauses.append(
            " AND (matched.side_a_concept_id = ANY(%(source_concept_ids)s::uuid[])"
            " OR matched.side_b_concept_id = ANY(%(source_concept_ids)s::uuid[]))"
        )
        params["source_concept_ids"] = source_concept_ids

    if scope.source_scheme_id:
        clauses.append(
            " AND (scheme_a.scheme_id = %(source_scheme_id)s::uuid"
            " OR scheme_b.scheme_id = %(source_scheme_id)s::uuid)"
        )
        params["source_scheme_id"] = str(scope.source_scheme_id)

    if scope.target_scheme_id:
        clauses.append(
            " AND (scheme_a.scheme_id = %(target_scheme_id)s::uuid"
            " OR scheme_b.scheme_id = %(target_scheme_id)s::uuid)"
        )
        params["target_scheme_id"] = str(scope.target_scheme_id)

    if scope.cross_scheme_only:
        clauses.append(" AND scheme_a.scheme_id IS DISTINCT FROM scheme_b.scheme_id")

    return "".join(clauses), params


def _needs_scheme_lookup(scope):
    return bool(
        scope.source_scheme_id or scope.target_scheme_id or scope.cross_scheme_only
    )


def _pair_query(match_sql, scope, source_concept_ids):
    """Wrap a signal's join in the scope narrowing.

    `match_sql` yields `side_a_concept_id`, `side_b_concept_id` and `evidence`.
    The pair is re-ordered lowest id first here so the same two concepts are
    never recorded under opposite names, whichever way the signal found them.

    Which scheme each concept belongs to is only worked out when a narrowing
    actually asks: the lookup spans every concept in the database, and most runs
    never consult it.
    """
    scope_sql, params = _scope_clauses(scope, source_concept_ids)

    scheme_cte = ""
    scheme_joins = ""
    if _needs_scheme_lookup(scope):
        scheme_cte = f"WITH concept_scheme AS ({_CONCEPT_SCHEME_SQL})"
        scheme_joins = """
          LEFT JOIN concept_scheme scheme_a
                 ON scheme_a.concept_id = matched.side_a_concept_id
          LEFT JOIN concept_scheme scheme_b
                 ON scheme_b.concept_id = matched.side_b_concept_id
        """

    sql = f"""
        {scheme_cte}
        SELECT DISTINCT
               LEAST(matched.side_a_concept_id::text,
                     matched.side_b_concept_id::text) AS concept_a,
               GREATEST(matched.side_a_concept_id::text,
                        matched.side_b_concept_id::text) AS concept_b,
               matched.evidence
          FROM ({match_sql}) matched
          {scheme_joins}
         WHERE true{scope_sql}
    """
    return sql, params


def _run_pair_query(sql, params):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for concept_a, concept_b, evidence in cursor.fetchall():
            yield concept_a, concept_b, evidence


def _scoped_side_sql(value_sql, source_concept_ids):
    """Return (sql, pairing_clause, params) for one side of a signal's self-join.

    With no source ids every pair is computed once, by keeping only the half of
    the join where the second id sorts higher. With source ids one side is
    pinned to them instead -- turning a scan of the whole corpus into a lookup
    of a handful of rows -- and the outer DISTINCT collapses the pair, which is
    then found from both directions.
    """
    if source_concept_ids is None:
        return value_sql, "side_b.concept_id::text > side_a.concept_id::text", {}

    scoped_sql = f"""
        SELECT * FROM ({value_sql}) scoped_side
         WHERE scoped_side.concept_id = ANY(%(source_concept_ids)s::uuid[])
    """
    return (
        scoped_sql,
        "side_b.concept_id <> side_a.concept_id",
        {"source_concept_ids": source_concept_ids},
    )


def find_exact_label_pairs(scope, same_language_only=True):
    """Concepts sharing a label, ignoring case and surrounding whitespace."""
    source_concept_ids = scope.resolve_source_concept_ids()
    side_a_sql, pairing_clause, pushdown_params = _scoped_side_sql(
        _LABEL_SQL, source_concept_ids
    )
    language_clause = (
        " AND side_b.language IS NOT DISTINCT FROM side_a.language"
        if same_language_only
        else ""
    )

    match_sql = f"""
        SELECT side_a.concept_id AS side_a_concept_id,
               side_b.concept_id AS side_b_concept_id,
               side_a.content AS evidence
          FROM ({side_a_sql}) side_a
          JOIN ({_LABEL_SQL}) side_b
            ON side_b.content = side_a.content
           AND {pairing_clause}
           {language_clause}
    """
    sql, scope_params = _pair_query(match_sql, scope, None)
    return _run_pair_query(sql, {**scope_params, **pushdown_params})


def find_shared_uri_pairs(scope):
    """Concepts carrying the same URI.

    A URI is globally meaningful, so two concepts sharing one are almost
    certainly the same concept.
    """
    source_concept_ids = scope.resolve_source_concept_ids()
    side_a_sql, pairing_clause, pushdown_params = _scoped_side_sql(
        _URI_SQL, source_concept_ids
    )

    match_sql = f"""
        SELECT side_a.concept_id AS side_a_concept_id,
               side_b.concept_id AS side_b_concept_id,
               side_a.uri AS evidence
          FROM ({side_a_sql}) side_a
          JOIN ({_URI_SQL}) side_b
            ON side_b.uri = side_a.uri
           AND {pairing_clause}
    """
    sql, scope_params = _pair_query(match_sql, scope, None)
    return _run_pair_query(sql, {**scope_params, **pushdown_params})


def find_decided_pairs():
    """Pairs an editor has already settled, in canonical order.

    A pair already linked by an exactMatch tile, or already recorded in
    ConceptMerge, is not a suggestion -- it is a decision. Suggesting it again
    would put answered work back in the queue.
    """
    decided = set()

    for survivor_id, absorbed_id in ConceptMerge.objects.values_list(
        "survivor_concept_id", "absorbed_concept_id"
    ):
        decided.add(ConceptMatchCandidate.order_concept_ids(survivor_id, absorbed_id))

    # An exactMatch names the other concept by URI rather than by id, so the
    # link is resolved back through the URI tiles.
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT match_tile.resourceinstanceid, uri_tile.resourceinstanceid
              FROM tiles match_tile
              JOIN tiles uri_tile
                ON uri_tile.nodegroupid = '{URI_NODEGROUP}'
               AND lower(btrim(uri_tile.tiledata ->> '{URI_CONTENT_NODE}'))
                   = lower(btrim(match_tile.tiledata ->> '{MATCH_STATUS_COMPARATE_NODE}'))
             WHERE match_tile.nodegroupid = '{MATCH_STATUS_NODEGROUP}'
               AND match_tile.resourceinstanceid <> uri_tile.resourceinstanceid
            """
        )
        for matching_concept_id, matched_concept_id in cursor.fetchall():
            decided.add(
                ConceptMatchCandidate.order_concept_ids(
                    matching_concept_id, matched_concept_id
                )
            )

    return decided


def mark_pairs_settled(pairs, status, user=None):
    """Record that these pairs have been decided, wherever they are queued.

    A pair can be suggested by more than one run, and settling it in one place
    settles it everywhere -- otherwise a reviewer working through an older run
    is asked again about concepts that have already been linked or merged.

    Only pending candidates are touched, so a decision already recorded is not
    overwritten by a later one.
    """
    canonical_pairs = {
        ConceptMatchCandidate.order_concept_ids(first_id, second_id)
        for first_id, second_id in pairs
    }
    if not canonical_pairs:
        return 0

    matching_pairs = Q()
    for concept_a, concept_b in canonical_pairs:
        matching_pairs |= Q(concept_a_id=concept_a, concept_b_id=concept_b)

    return ConceptMatchCandidate.objects.filter(
        matching_pairs, status=ConceptMatchCandidate.STATUS_PENDING
    ).update(
        status=status,
        reviewed_by=user if user is not None and user.is_authenticated else None,
        reviewed_at=timezone.now(),
    )


def collect_candidates(scope, signals=EXACT_SIGNALS, same_language_only=True):
    """Gather every suggested pair, best signal per pair.

    Signals can suggest the same pair for different reasons; the strongest one
    is kept so the pair appears once, described by its best evidence.
    """
    unknown_signals = set(signals) - set(EXACT_SIGNALS)
    if unknown_signals:
        raise ConceptMatchError(
            f"Unsupported signal(s): {', '.join(sorted(unknown_signals))}"
        )

    decided_pairs = find_decided_pairs()
    candidates_by_pair = {}

    # Ordered strongest first, so a pair found twice keeps the better reason.
    signal_sources = [
        (SIGNAL_SHARED_IDENTIFIER, lambda: find_shared_uri_pairs(scope)),
        (
            SIGNAL_EXACT_LABEL,
            lambda: find_exact_label_pairs(scope, same_language_only),
        ),
    ]

    for signal, produce_pairs in signal_sources:
        if signal not in signals:
            continue
        for concept_a, concept_b, evidence in produce_pairs():
            pair = (concept_a, concept_b)
            if pair in decided_pairs or pair in candidates_by_pair:
                continue
            candidates_by_pair[pair] = (signal, evidence)

    return candidates_by_pair


def run_detection(
    scope,
    signals=EXACT_SIGNALS,
    same_language_only=True,
    user=None,
    log=print,
):
    """Detect matches and store them as a reviewable run."""
    run = ConceptMatchRun.objects.create(
        user=user if user is not None and user.is_authenticated else None,
        status=ConceptMatchRun.STATUS_RUNNING,
        parameters={
            **scope.as_parameters(),
            "signals": list(signals),
            "same_language_only": same_language_only,
        },
    )

    try:
        candidates_by_pair = collect_candidates(scope, signals, same_language_only)
        log(f"  found {len(candidates_by_pair):,} candidate pairs")

        candidates = [
            ConceptMatchCandidate(
                run=run,
                concept_a_id=concept_a,
                concept_b_id=concept_b,
                # Both signals implemented here are exact matches on a value,
                # so the pair is either suggested or it is not.
                score=1.0,
                signal=signal,
                evidence=evidence or "",
            )
            for (concept_a, concept_b), (signal, evidence) in (
                candidates_by_pair.items()
            )
        ]

        with transaction.atomic():
            ConceptMatchCandidate.objects.bulk_create(
                candidates, batch_size=CANDIDATE_BATCH_SIZE
            )
            run.candidate_count = len(candidates)
            run.status = ConceptMatchRun.STATUS_COMPLETE
            run.finished = timezone.now()
            run.save(update_fields=["candidate_count", "status", "finished"])
    except Exception as detection_error:
        run.status = ConceptMatchRun.STATUS_FAILED
        run.error_message = str(detection_error)
        run.finished = timezone.now()
        run.save(update_fields=["status", "error_message", "finished"])
        raise

    return run
