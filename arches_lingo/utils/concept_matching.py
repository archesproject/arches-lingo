"""Suggest pairs of concepts that probably mean the same thing.

Pairs already settled by an exactMatch or a merge are never suggested again.
Written as SQL over `tiles` rather than the ORM because the trigram index is
defined on the raw `tiledata ->> node_id` expression.
"""

import json
import logging
import threading
from contextlib import contextmanager

from django.conf import settings
from django.db import connection, connections, transaction
from django.db.models import Q
from django.utils import timezone

from arches_controlled_lists.models import ListItem

from arches_lingo.const import (
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    EXACT_MATCH_LIST_ITEM_ID,
    MATCH_STATUS_COMPARATE_NODE,
    MATCH_STATUS_NODEGROUP,
    MATCH_STATUS_RELATION_NODE,
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
from arches_lingo.utils.concept_lifecycle import RETIRED_STATE_ID

SIGNAL_SHARED_IDENTIFIER = ConceptMatchCandidate.SIGNAL_SHARED_IDENTIFIER
SIGNAL_EXACT_LABEL = ConceptMatchCandidate.SIGNAL_EXACT_LABEL

SIGNAL_TRIGRAM = ConceptMatchCandidate.SIGNAL_TRIGRAM

EXACT_SIGNALS = (SIGNAL_SHARED_IDENTIFIER, SIGNAL_EXACT_LABEL)
ALL_SIGNALS = EXACT_SIGNALS + (SIGNAL_TRIGRAM,)

# Postgres's own default of 0.3 is far too loose for a vocabulary of any size.
DEFAULT_SIMILARITY_THRESHOLD = 0.7
MIN_SIMILARITY_THRESHOLD = 0.3
MAX_SIMILARITY_THRESHOLD = 1.0

# Each label is an independent, CPU-bound index probe, so the fuzzy signal scales
# well past Postgres's default of two workers. Capped by max_parallel_workers.
TRIGRAM_PARALLEL_WORKERS = getattr(settings, "LINGO_MATCH_PARALLEL_WORKERS", 8)

TRIGRAM_WORK_MEM = getattr(settings, "LINGO_MATCH_WORK_MEM", "64MB")

# Each slice commits as it finishes, so more slices means more frequent progress
# at the cost of re-scanning the driving side once per slice.
MATCH_SLICE_COUNT = getattr(settings, "LINGO_MATCH_SLICE_COUNT", 16)

# Must stay well inside STALE_RUN_SECONDS, after which a silent run is reaped.
HEARTBEAT_INTERVAL_SECONDS = 30

# Temp tables dropped by name, so the names must be distinctive.
_SCHEME_SCOPE_TABLE = "lingo_match_concept_scheme"
_FOUND_PAIRS_TABLE = "lingo_match_found_pairs"

logger = logging.getLogger(__name__)


@contextmanager
def _heartbeat_while_working(run):
    """Keep `run` from being reaped while a single long query holds this thread.

    A separate thread because one query can run for minutes; if the worker
    dies the thread dies with it, and the run is reaped as it should be.
    """
    if run is None:
        yield
        return

    stop_beating = threading.Event()

    def beat():
        try:
            while not stop_beating.wait(HEARTBEAT_INTERVAL_SECONDS):
                try:
                    ConceptMatchRun.objects.filter(pk=run.pk).update(
                        last_progress=timezone.now()
                    )
                except Exception:
                    # A missed heartbeat is not worth failing the run over.
                    logger.warning(
                        "Could not record progress for match run %s.",
                        run.pk,
                        exc_info=True,
                    )
        finally:
            # Only this thread can close its own connection.
            connections.close_all()

    heartbeat_thread = threading.Thread(
        target=beat, name=f"lingo-match-run-{run.pk}", daemon=True
    )
    heartbeat_thread.start()
    try:
        yield
    finally:
        stop_beating.set()
        heartbeat_thread.join(timeout=HEARTBEAT_INTERVAL_SECONDS)


class ConceptMatchError(Exception):
    """A run that cannot proceed as asked."""


class ConceptMatchRunCancelled(Exception):
    """The run was deleted while detection was working.

    Deleting the row is how a run is cancelled, since celery cannot reliably
    terminate a task already executing under the solo pool.
    """


class MatchScope:
    """Which concepts a run compares; leaving everything unset compares all."""

    def __init__(
        self,
        scheme_ids=None,
        source_concept_set_id=None,
        source_concept_ids=None,
        cross_scheme_only=False,
    ):
        self.scheme_ids = [str(scheme_id) for scheme_id in scheme_ids or []]
        self.source_concept_set_id = source_concept_set_id
        self.source_concept_ids = [
            str(concept_id) for concept_id in source_concept_ids or []
        ]
        self.cross_scheme_only = cross_scheme_only

    def as_parameters(self):
        return {
            "scheme_ids": self.scheme_ids,
            "source_concept_set_id": self.source_concept_set_id,
            "source_concept_ids": self.source_concept_ids,
            "cross_scheme_only": self.cross_scheme_only,
        }

    def resolve_source_concept_ids(self):
        """Source ids, with a concept set resolved to its members; else None."""
        if self.source_concept_ids:
            return self.source_concept_ids

        if self.source_concept_set_id is not None:
            member_ids = ConceptSetMember.objects.filter(
                concept_set_id=self.source_concept_set_id
            ).values_list("concept_id", flat=True)
            return [str(member_id) for member_id in member_ids]

        return None


# Reads top_concept_of as well as part_of_scheme so scoping to a scheme does not
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

_LABEL_SQL = f"""
    SELECT resourceinstanceid AS concept_id,
           lower(btrim(tiledata ->> '{CONCEPT_NAME_CONTENT_NODE}')) AS content,
           tiledata ->> '{CONCEPT_NAME_LANGUAGE_NODE}' AS language
      FROM tiles
     WHERE nodegroupid = '{CONCEPT_NAME_NODEGROUP}'
       AND btrim(coalesce(tiledata ->> '{CONCEPT_NAME_CONTENT_NODE}', '')) <> ''
"""

# Left un-normalized to match the expression migration 0012 indexed; pg_trgm
# lowercases internally, so nothing is lost.
_INDEXED_LABEL_SQL = f"""
    SELECT resourceinstanceid AS concept_id,
           tiledata ->> '{CONCEPT_NAME_CONTENT_NODE}' AS content,
           tiledata ->> '{CONCEPT_NAME_LANGUAGE_NODE}' AS language
      FROM tiles
     WHERE nodegroupid = '{CONCEPT_NAME_NODEGROUP}'
       AND btrim(coalesce(tiledata ->> '{CONCEPT_NAME_CONTENT_NODE}', '')) <> ''
"""

# Bare identifiers are deliberately not compared: ConceptIdentifierCounter
# allocates them per scheme, so equality across schemes means nothing.
_URI_SQL = f"""
    SELECT resourceinstanceid AS concept_id,
           lower(btrim(tiledata ->> '{URI_CONTENT_NODE}')) AS uri
      FROM tiles
     WHERE nodegroupid = '{URI_NODEGROUP}'
       AND btrim(coalesce(tiledata ->> '{URI_CONTENT_NODE}', '')) <> ''
"""


def get_scheme_ids_for_concepts(concept_ids):
    """Return {concept id: scheme id} for the concepts given."""
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


def _scope_clauses(scope):
    """Return (sql, params) narrowing which pairs a run keeps by scheme.

    Source concepts are not narrowed here: each signal pins one side of its join
    to them instead (see _scoped_side_sql).
    """
    clauses = []
    params = {}

    if scope.scheme_ids:
        clauses.append(
            " AND scheme_a.scheme_id = ANY(%(scheme_ids)s::uuid[])"
            " AND scheme_b.scheme_id = ANY(%(scheme_ids)s::uuid[])"
        )
        params["scheme_ids"] = scope.scheme_ids

    if scope.cross_scheme_only:
        clauses.append(" AND scheme_a.scheme_id IS DISTINCT FROM scheme_b.scheme_id")

    return "".join(clauses), params


def _needs_scheme_lookup(scope):
    return bool(scope.scheme_ids or scope.cross_scheme_only)


def _pair_query(match_sql, scope, score_sql="1.0"):
    """Wrap a signal's join in the scope narrowing, ordering each pair.

    Retired concepts are left out here, on the pairs found, rather than in each
    side's label query, so the trigram index probe stays as migration 0012
    planned it.
    """
    scope_sql, params = _scope_clauses(scope)
    params["retired_state_id"] = str(RETIRED_STATE_ID)

    scheme_joins = ""
    if _needs_scheme_lookup(scope):
        # A temp table rather than a CTE; see _prepare_scheme_lookup.
        scheme_joins = f"""
          LEFT JOIN {_SCHEME_SCOPE_TABLE} scheme_a
                 ON scheme_a.concept_id = matched.side_a_concept_id
          LEFT JOIN {_SCHEME_SCOPE_TABLE} scheme_b
                 ON scheme_b.concept_id = matched.side_b_concept_id
        """

    sql = f"""
        SELECT DISTINCT ON (concept_a, concept_b)
               LEAST(matched.side_a_concept_id::text,
                     matched.side_b_concept_id::text) AS concept_a,
               GREATEST(matched.side_a_concept_id::text,
                        matched.side_b_concept_id::text) AS concept_b,
               matched.evidence,
               {score_sql} AS score
          FROM ({match_sql}) matched
          {scheme_joins}
         WHERE NOT EXISTS (
                   SELECT 1
                     FROM resource_instances retired
                    WHERE retired.resourceinstanceid IN (
                              matched.side_a_concept_id, matched.side_b_concept_id
                          )
                      AND retired.resource_instance_lifecycle_state_id
                          = %(retired_state_id)s::uuid
               ){scope_sql}
         ORDER BY concept_a, concept_b, score DESC
    """
    return sql, params


def _prepare_scheme_lookup(scope):
    """Build the concept-to-scheme lookup as an analysed temp table.

    As a CTE it is badly underestimated and parallel-restricted, so the planner
    loses both the trigram index and its workers; with statistics it does not.
    """
    if not _needs_scheme_lookup(scope):
        return

    where_clause = ""
    params = {}
    if scope.scheme_ids:
        where_clause = " WHERE cs.scheme_id = ANY(%(scheme_ids)s::uuid[])"
        params["scheme_ids"] = scope.scheme_ids

    with connection.cursor() as cursor:
        # ON COMMIT DROP never fires for an atomic block nested in an outer
        # transaction (a savepoint), so drop by name rather than trust it.
        cursor.execute(f"DROP TABLE IF EXISTS {_SCHEME_SCOPE_TABLE}")
        cursor.execute(
            f"""
            CREATE TEMP TABLE {_SCHEME_SCOPE_TABLE} ON COMMIT DROP AS
            SELECT cs.concept_id, cs.scheme_id
              FROM ({_CONCEPT_SCHEME_SQL}) cs{where_clause}
            """,
            params,
        )
        cursor.execute(f"CREATE INDEX ON {_SCHEME_SCOPE_TABLE} (concept_id)")
        cursor.execute(f"ANALYZE {_SCHEME_SCOPE_TABLE}")


def _scoped_side_sql(value_sql, source_concept_ids, slice_predicate=""):
    """Return (sql, pairing_clause, params) for one side of a signal's self-join.

    With source ids one side is pinned to them and the outer DISTINCT collapses
    pairs found from both directions. A scheme scope is not applied here: the
    planner already pushes it down, and repeating it only adds a join.
    """
    if source_concept_ids is None:
        if not slice_predicate:
            return value_sql, "side_b.concept_id::text > side_a.concept_id::text", {}
        sliced_sql = f"""
            SELECT * FROM ({value_sql}) scoped_side
             WHERE true{slice_predicate}
        """
        return (
            sliced_sql,
            "side_b.concept_id::text > side_a.concept_id::text",
            {},
        )

    scoped_sql = f"""
        SELECT * FROM ({value_sql}) scoped_side
         WHERE scoped_side.concept_id = ANY(%(source_concept_ids)s::uuid[])
    """
    return (
        scoped_sql,
        "side_b.concept_id <> side_a.concept_id",
        {"source_concept_ids": source_concept_ids},
    )


def _driving_side_slices(source_concept_ids):
    """Split a corpus-wide fuzzy search into queries that each commit as they end.

    Slicing on the lower-id side keeps each pair inside one slice. Only the
    fuzzy signal is sliced: the exact signals are hash joins, which slicing
    would rebuild once per slice.
    """
    if source_concept_ids is not None:
        return [""]
    return [
        # Masked rather than abs(), which errors on the minimum int4. %% because
        # parameters are always passed, so psycopg would read % as a placeholder.
        f" AND (hashtext(scoped_side.concept_id::text) & 2147483647)"
        f" %% {MATCH_SLICE_COUNT} = {slice_index}"
        for slice_index in range(MATCH_SLICE_COUNT)
    ]


def _language_clause(same_language_only):
    return (
        " AND side_b.language IS NOT DISTINCT FROM side_a.language"
        if same_language_only
        else ""
    )


def _exact_label_pair_queries(scope, same_language_only):
    source_concept_ids = scope.resolve_source_concept_ids()
    side_a_sql, pairing_clause, pushdown_params = _scoped_side_sql(
        _LABEL_SQL, source_concept_ids
    )
    match_sql = f"""
        SELECT side_a.concept_id AS side_a_concept_id,
               side_b.concept_id AS side_b_concept_id,
               side_a.content AS evidence
          FROM ({side_a_sql}) side_a
          JOIN ({_LABEL_SQL}) side_b
            ON side_b.content = side_a.content
           AND {pairing_clause}
           {_language_clause(same_language_only)}
    """
    sql, scope_params = _pair_query(match_sql, scope)
    return [(sql, {**scope_params, **pushdown_params})]


def _shared_uri_pair_queries(scope):
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
    sql, scope_params = _pair_query(match_sql, scope)
    return [(sql, {**scope_params, **pushdown_params})]


def _similar_label_pair_queries(scope, same_language_only):
    source_concept_ids = scope.resolve_source_concept_ids()
    queries = []
    for slice_predicate in _driving_side_slices(source_concept_ids):
        side_a_sql, pairing_clause, pushdown_params = _scoped_side_sql(
            _INDEXED_LABEL_SQL, source_concept_ids, slice_predicate
        )
        match_sql = f"""
            SELECT side_a.concept_id AS side_a_concept_id,
                   side_b.concept_id AS side_b_concept_id,
                   side_a.content || ' ~ ' || side_b.content AS evidence,
                   similarity(side_a.content, side_b.content) AS pair_score
              FROM ({side_a_sql}) side_a
              JOIN ({_INDEXED_LABEL_SQL}) side_b
                ON side_b.content %% side_a.content
               AND side_b.content <> side_a.content
               AND {pairing_clause}
               {_language_clause(same_language_only)}
        """
        sql, scope_params = _pair_query(
            match_sql, scope, score_sql="matched.pair_score"
        )
        queries.append((sql, {**scope_params, **pushdown_params}))
    return queries


def _signal_queries(signal, scope, same_language_only):
    if signal == SIGNAL_SHARED_IDENTIFIER:
        return _shared_uri_pair_queries(scope)
    if signal == SIGNAL_EXACT_LABEL:
        return _exact_label_pair_queries(scope, same_language_only)
    return _similar_label_pair_queries(scope, same_language_only)


def _apply_trigram_session_tuning(similarity_threshold):
    """SET LOCAL, not SET, so nothing leaks onto a connection Django reuses."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SET LOCAL pg_trgm.similarity_threshold = %s", [similarity_threshold]
        )
        cursor.execute(
            f"SET LOCAL max_parallel_workers_per_gather = {TRIGRAM_PARALLEL_WORKERS}"
        )
        # Every row drives an independent index probe, so parallelism always
        # pays here, whatever the planner's default costs assume.
        cursor.execute("SET LOCAL parallel_setup_cost = 0")
        cursor.execute("SET LOCAL parallel_tuple_cost = 0")
        cursor.execute(f"SET LOCAL work_mem = '{TRIGRAM_WORK_MEM}'")


def _decided_pairs_sql():
    """Return (sql, params) for pairs settled by a merge or an exactMatch.

    Other match relations (close, broad, ...) leave a pair open, since the two
    may still be duplicates.
    """
    exact_match_uri = ListItem.objects.get(
        pk=EXACT_MATCH_LIST_ITEM_ID
    ).build_tile_value()["uri"]
    sql = f"""
        SELECT LEAST(survivor_concept_id::text, absorbed_concept_id::text)
                   AS concept_a,
               GREATEST(survivor_concept_id::text, absorbed_concept_id::text)
                   AS concept_b
          FROM {ConceptMerge._meta.db_table}
        UNION
        SELECT LEAST(match_tile.resourceinstanceid::text,
                     uri_tile.resourceinstanceid::text),
               GREATEST(match_tile.resourceinstanceid::text,
                        uri_tile.resourceinstanceid::text)
          FROM tiles match_tile
          JOIN tiles uri_tile
            ON uri_tile.nodegroupid = '{URI_NODEGROUP}'
           AND lower(btrim(uri_tile.tiledata ->> '{URI_CONTENT_NODE}'))
               = lower(btrim(match_tile.tiledata ->> '{MATCH_STATUS_COMPARATE_NODE}'))
         WHERE match_tile.nodegroupid = '{MATCH_STATUS_NODEGROUP}'
           AND match_tile.tiledata -> '{MATCH_STATUS_RELATION_NODE}'
               @> %(exact_match_relation)s::jsonb
           AND match_tile.resourceinstanceid <> uri_tile.resourceinstanceid
    """
    return sql, {"exact_match_relation": json.dumps([{"uri": exact_match_uri}])}


def _store_pairs(run, signal, sql, params, scope, similarity_threshold):
    """Run one pair query and store its new pairs, returning how many.

    CREATE TEMP TABLE AS rather than a cursor, because Postgres never plans a
    declared cursor in parallel. A pair a stronger signal already stored keeps
    that signal.
    """
    decided_sql, decided_params = _decided_pairs_sql()
    with transaction.atomic():
        if signal == SIGNAL_TRIGRAM:
            _apply_trigram_session_tuning(similarity_threshold)
        _prepare_scheme_lookup(scope)
        with connection.cursor() as cursor:
            # See _prepare_scheme_lookup for why ON COMMIT DROP is not enough.
            cursor.execute(f"DROP TABLE IF EXISTS {_FOUND_PAIRS_TABLE}")
            cursor.execute(
                f"CREATE TEMP TABLE {_FOUND_PAIRS_TABLE} ON COMMIT DROP AS {sql}",
                params,
            )
            cursor.execute(
                f"""
                INSERT INTO {ConceptMatchCandidate._meta.db_table}
                       (run_id, concept_a_id, concept_b_id, score, signal,
                        evidence, status)
                SELECT %(run_id)s, found.concept_a::uuid, found.concept_b::uuid,
                       found.score, %(signal)s, coalesce(found.evidence, ''),
                       %(pending_status)s
                  FROM {_FOUND_PAIRS_TABLE} found
                 WHERE NOT EXISTS (
                       SELECT 1
                         FROM ({decided_sql}) decided
                        WHERE decided.concept_a = found.concept_a
                          AND decided.concept_b = found.concept_b
                 )
                ON CONFLICT (run_id, concept_a_id, concept_b_id) DO NOTHING
                """,
                {
                    **decided_params,
                    "run_id": run.pk,
                    "signal": signal,
                    "pending_status": ConceptMatchCandidate.STATUS_PENDING,
                },
            )
            return cursor.rowcount


def mark_pairs_settled(pairs, status, user=None):
    """Settle these pairs in every run, whatever was decided about them before.

    Linking or merging is done to the concepts themselves, so it outranks an
    earlier dismissal; only a merge outranks a link.
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

    return (
        ConceptMatchCandidate.objects.filter(matching_pairs)
        .exclude(status__in={status, ConceptMatchCandidate.STATUS_MERGED})
        .update(
            status=status,
            reviewed_by=user if user is not None and user.is_authenticated else None,
            reviewed_at=timezone.now(),
        )
    )


def hand_pending_pairs_to_survivor(absorbed_concept_id, survivor_concept_id):
    """Re-point the absorbed concept's outstanding pairs at the survivor.

    Once a merge retires or deletes the absorbed concept, a pair with it can no
    longer be merged or linked both ways; the question it raised is now one
    about the survivor. A pair the run already holds for the survivor is
    dropped rather than asked twice.
    """
    absorbed_concept_id = str(absorbed_concept_id)
    survivor_concept_id = str(survivor_concept_id)
    pending_with_absorbed = ConceptMatchCandidate.objects.filter(
        Q(concept_a_id=absorbed_concept_id) | Q(concept_b_id=absorbed_concept_id),
        status=ConceptMatchCandidate.STATUS_PENDING,
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


def restore_dismissed(run, user=None, candidate_ids=None):
    """Return dismissed pairs to the queue, returning (restored, left dismissed).

    A pair linked or merged since it was dismissed stays dismissed.
    """
    decided_sql, decided_params = _decided_pairs_sql()
    params = {
        **decided_params,
        "run_id": run.pk,
        "pending_status": ConceptMatchCandidate.STATUS_PENDING,
        "dismissed_status": ConceptMatchCandidate.STATUS_DISMISSED,
        "reviewed_by_id": (
            user.pk if user is not None and user.is_authenticated else None
        ),
        "reviewed_at": timezone.now(),
    }
    candidate_clause = ""
    dismissed_candidates = ConceptMatchCandidate.objects.filter(
        run=run, status=ConceptMatchCandidate.STATUS_DISMISSED
    )
    if candidate_ids is not None:
        candidate_clause = " AND candidate.id = ANY(%(candidate_ids)s)"
        params["candidate_ids"] = list(candidate_ids)
        dismissed_candidates = dismissed_candidates.filter(pk__in=candidate_ids)

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE {ConceptMatchCandidate._meta.db_table} candidate
               SET status = %(pending_status)s,
                   reviewed_by_id = %(reviewed_by_id)s,
                   reviewed_at = %(reviewed_at)s
             WHERE candidate.run_id = %(run_id)s
               AND candidate.status = %(dismissed_status)s{candidate_clause}
               AND NOT EXISTS (
                   SELECT 1
                     FROM ({decided_sql}) decided
                    WHERE decided.concept_a = candidate.concept_a_id::text
                      AND decided.concept_b = candidate.concept_b_id::text
               )
            """,
            params,
        )
        restored_count = cursor.rowcount

    return restored_count, dismissed_candidates.count()


def validate_detection_options(signals, similarity_threshold):
    unknown_signals = set(signals) - set(ALL_SIGNALS)
    if unknown_signals:
        raise ConceptMatchError(
            f"Unsupported signal(s): {', '.join(sorted(unknown_signals))}"
        )
    if not (
        MIN_SIMILARITY_THRESHOLD <= similarity_threshold <= MAX_SIMILARITY_THRESHOLD
    ):
        raise ConceptMatchError(
            f"The similarity threshold must be between {MIN_SIMILARITY_THRESHOLD}"
            f" and {MAX_SIMILARITY_THRESHOLD}."
        )


def _store_candidates(
    run, scope, signals, same_language_only, similarity_threshold, log
):
    stored_count = 0
    for signal in ALL_SIGNALS:
        if signal not in signals:
            continue
        for sql, params in _signal_queries(signal, scope, same_language_only):
            if not ConceptMatchRun.objects.filter(pk=run.pk).exists():
                raise ConceptMatchRunCancelled
            stored_count += _store_pairs(
                run, signal, sql, params, scope, similarity_threshold
            )
            ConceptMatchRun.objects.filter(pk=run.pk).update(
                candidate_count=stored_count, last_progress=timezone.now()
            )
            log(f"  {stored_count:,} candidate pairs so far")
    return stored_count


def run_detection(
    scope,
    signals=EXACT_SIGNALS,
    same_language_only=True,
    similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD,
    user=None,
    log=print,
    run=None,
    name="",
):
    """Detect matches and store them as a reviewable run, or fill in `run`."""
    validate_detection_options(signals, similarity_threshold)

    if run is None:
        run = ConceptMatchRun.objects.create(
            user=user if user is not None and user.is_authenticated else None,
            name=name,
            status=ConceptMatchRun.STATUS_RUNNING,
            last_progress=timezone.now(),
            parameters={
                **scope.as_parameters(),
                "signals": list(signals),
                "same_language_only": same_language_only,
                "similarity_threshold": similarity_threshold,
            },
        )
    else:
        run.status = ConceptMatchRun.STATUS_RUNNING
        run.last_progress = timezone.now()
        run.save(update_fields=["status", "last_progress"])

    try:
        with _heartbeat_while_working(run):
            written_count = _store_candidates(
                run, scope, signals, same_language_only, similarity_threshold, log
            )

        run.candidate_count = written_count
        run.status = ConceptMatchRun.STATUS_COMPLETE
        run.finished = timezone.now()
        ConceptMatchRun.objects.filter(pk=run.pk).update(
            candidate_count=run.candidate_count,
            status=run.status,
            finished=run.finished,
        )
        log(f"  found {written_count:,} candidate pairs")
    except ConceptMatchRunCancelled:
        log("  the run was deleted while it was working; stopping")
        return None
    except Exception as detection_error:
        # A run deleted mid-query fails the commit on the foreign key; that is
        # a cancellation, not a failure.
        if not ConceptMatchRun.objects.filter(pk=run.pk).exists():
            log("  the run was deleted while it was working; stopping")
            return None
        run.status = ConceptMatchRun.STATUS_FAILED
        run.error_message = str(detection_error)
        run.finished = timezone.now()
        ConceptMatchRun.objects.filter(pk=run.pk).update(
            status=run.status,
            error_message=run.error_message,
            finished=run.finished,
        )
        raise

    return run
