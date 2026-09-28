"""Find concepts that probably mean the same thing.

Detection produces *pairs*: two concepts and the reason they were suggested. A
pair is a suggestion, not a decision, so the candidates it writes carry a review
state and the pairs an editor has already settled -- by linking them with an
exactMatch, or by merging one into the other -- are never suggested again.

Signals are independent and can be run in any combination:

  * `shared_identifier` -- the concepts carry the same URI
  * `exact_label` -- a label on one matches a label on the other exactly
  * `trigram` -- a label on one is similar to a label on the other (`pg_trgm`)

Everything is expressed as SQL over `tiles` rather than through the ORM: the
label corpus runs to hundreds of thousands of rows, and the trigram index the
fuzzy signal will need is defined on the raw `tiledata ->> node_id` expression.
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
    CONCEPTS_GRAPH_ID,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    EXACT_MATCH_LIST_ITEM_ID,
    IDENTIFIER_CONTENT_NODE,
    IDENTIFIER_NODEGROUP,
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

SIGNAL_SHARED_IDENTIFIER = ConceptMatchCandidate.SIGNAL_SHARED_IDENTIFIER
SIGNAL_EXACT_LABEL = ConceptMatchCandidate.SIGNAL_EXACT_LABEL

SIGNAL_TRIGRAM = ConceptMatchCandidate.SIGNAL_TRIGRAM

EXACT_SIGNALS = (SIGNAL_SHARED_IDENTIFIER, SIGNAL_EXACT_LABEL)
ALL_SIGNALS = EXACT_SIGNALS + (SIGNAL_TRIGRAM,)

# Postgres defaults this to 0.3, which is far too loose for a vocabulary of any
# size; see find_similar_label_pairs.
DEFAULT_SIMILARITY_THRESHOLD = 0.7
# Below Postgres's own default nearly every label pairs with every other.
MIN_SIMILARITY_THRESHOLD = 0.3
MAX_SIMILARITY_THRESHOLD = 1.0

# Comparing a vocabulary against itself is one index probe per label, each one
# CPU-bound on intersecting trigram posting lists and independent of the rest.
# Postgres allows two workers per gather by default, which leaves most of a
# server idle; measured 1.9x faster at eight on the AAT. Capped in practice by
# the server's own max_parallel_workers, so raising that is the deployment knob.
TRIGRAM_PARALLEL_WORKERS = getattr(settings, "LINGO_MATCH_PARALLEL_WORKERS", 8)

# Worth about 9% on the same measurement: enough of the bitmap stays exact to
# save some rechecks, but this is a distant second to parallelism.
TRIGRAM_WORK_MEM = getattr(settings, "LINGO_MATCH_WORK_MEM", "64MB")

# How many rows a server-side cursor pulls at a time when pairs are read back
# rather than stored. Bounds how much of a result set is ever in memory at once.
ROW_FETCH_SIZE = 2_000

# How many independent queries a corpus-wide fuzzy search is split into. Each
# slice commits its pairs as it finishes, so more slices means results and
# progress arrive more often, at the cost of re-scanning the driving side once
# per slice -- cheap next to the index probes it drives.
MATCH_SLICE_COUNT = getattr(settings, "LINGO_MATCH_SLICE_COUNT", 16)

# How often a run records that it is still alive while a query holds the thread.
# Comfortably inside the window after which a silent run is presumed dead.
HEARTBEAT_INTERVAL_SECONDS = 30

# The concept-to-scheme lookup a scoped run joins against, and the pairs one
# query found before they are stored. Named for what they are and who owns them:
# they are dropped by name, so they must not be something another part of the
# schema could plausibly be called.
_SCHEME_SCOPE_TABLE = "lingo_match_concept_scheme"
_FOUND_PAIRS_TABLE = "lingo_match_found_pairs"

logger = logging.getLogger(__name__)


@contextmanager
def _heartbeat_while_working(run):
    """Record that `run` is alive while a query holds this thread.

    Progress is recorded as each query's pairs are stored, but one query over a
    large vocabulary can hold the process for minutes, and a run that goes quiet
    for long enough is reaped as though its worker had died. So the reporting is
    done from a thread of its own -- idle but for one small update every half
    minute. If the worker dies, the thread dies with it and the run is reaped,
    which is the behaviour the reaper exists for.
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
                    # Losing a heartbeat is not worth failing a run over; the
                    # next one will do, and a real stall still gets reaped.
                    logger.warning(
                        "Could not record progress for match run %s.",
                        run.pk,
                        exc_info=True,
                    )
        finally:
            # This thread has its own connection, and it is the only one that
            # can close it.
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
    """The run was deleted while its detection was still working.

    Deleting the row is how a run is cancelled: celery cannot be relied on to
    terminate a task that is already executing -- the solo pool runs it in the
    same process as the worker -- so the run record is the control channel, and
    detection checks that it is still there each time it stores a batch.
    """


class MatchScope:
    """Which concepts a run compares.

    `scheme_ids` confines the run to those schemes: both concepts of a pair must
    belong to one of them, so a run scoped this way never returns a concept from
    a scheme that was not chosen. Leaving everything unset compares every concept
    with every other, which is what a whole-corpus duplicate sweep is.
    """

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

# The same labels, left exactly as the trigram index stores them. Comparing
# `lower(btrim(content))` would be a different expression from the one migration
# 0012 indexed, and the planner would fall back to reading every row instead.
# pg_trgm lowercases internally when it builds trigrams, so matching on the raw
# value costs nothing in accuracy.
_INDEXED_LABEL_SQL = f"""
    SELECT resourceinstanceid AS concept_id,
           tiledata ->> '{CONCEPT_NAME_CONTENT_NODE}' AS content,
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

    if scope.scheme_ids:
        # Both sides, not either: a run scoped to a set of schemes is a search
        # within them, so a pair reaching outside the set is not part of it.
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


def _pair_query(match_sql, scope, source_concept_ids, score_sql="1.0"):
    """Wrap a signal's join in the scope narrowing.

    `match_sql` yields `side_a_concept_id`, `side_b_concept_id` and `evidence`.
    The pair is re-ordered lowest id first here so the same two concepts are
    never recorded under opposite names, whichever way the signal found them.

    Which scheme each concept belongs to is only worked out when a narrowing
    actually asks: the lookup spans every concept in the database, and most runs
    never consult it.
    """
    scope_sql, params = _scope_clauses(scope, source_concept_ids)

    scheme_joins = ""
    if _needs_scheme_lookup(scope):
        # The joined table is the one _prepare_scheme_lookup builds in this
        # transaction, rather than a CTE; see the note there for why.
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
         WHERE true{scope_sql}
         ORDER BY concept_a, concept_b, score DESC
    """
    return sql, params


def count_labels_by_scheme():
    """Return (total labels, {scheme id: labels}) across the corpus.

    What a fuzzy run costs follows how many labels it has to compare, so this is
    what lets the interface say how long one is likely to take before anyone
    commits to starting it. Labels belonging to no scheme are counted in the
    total and in no scheme, which is right on both counts: an unscoped run
    compares them, and a scoped one does not.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT cs.scheme_id, count(*)
              FROM ({_INDEXED_LABEL_SQL}) labels
              JOIN ({_CONCEPT_SCHEME_SQL}) cs ON cs.concept_id = labels.concept_id
             GROUP BY cs.scheme_id
            """
        )
        labels_by_scheme = {
            str(scheme_id): count for scheme_id, count in cursor.fetchall()
        }
        cursor.execute(f"SELECT count(*) FROM ({_INDEXED_LABEL_SQL}) labels")
        total_labels = cursor.fetchone()[0]

    return total_labels, labels_by_scheme


def _prepare_scheme_lookup(scope):
    """Put the concept-to-scheme lookup in a temp table, inside this transaction.

    As a CTE it is estimated at 200 rows when it holds tens of thousands, and the
    planner then drives the whole query from it: one slice of a scoped fuzzy run
    measured over nine minutes against about eighty seconds unscoped, having lost
    both the trigram index and its six parallel workers. A `CTE Scan` is also
    parallel-restricted, so referencing one makes the outer plan serial whatever
    it estimates.

    A temp table can be analysed. With statistics the same query plans like the
    unscoped one -- 44,790 estimated rows rather than 1, the trigram index back,
    the workers back -- so a scope costs about what no scope costs instead of
    several times more.
    """
    if not _needs_scheme_lookup(scope):
        return

    where_clause = ""
    params = {}
    if scope.scheme_ids:
        where_clause = " WHERE cs.scheme_id = ANY(%(scheme_ids)s::uuid[])"
        params["scheme_ids"] = scope.scheme_ids

    with connection.cursor() as cursor:
        # ON COMMIT DROP only fires on a real commit, and an atomic block nested
        # inside another transaction -- every test, and anything that wraps a run
        # -- is a savepoint that never commits. So the table is dropped by name
        # rather than trusted to disappear on its own. The name is distinctive
        # enough that dropping it cannot take anything else with it.
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


def _run_pair_query(sql, params, scope, similarity_threshold=None):
    """Yield rows as they arrive, rather than buffering the whole result.

    For reading pairs back from a narrow scope; a run stores them with
    `_store_pairs` instead. psycopg fetches everything on execute() with an
    ordinary cursor, so this reads through a server-side one bounded by
    `itersize`.
    """
    with transaction.atomic():
        if similarity_threshold is not None:
            _apply_trigram_session_tuning(similarity_threshold)
        _prepare_scheme_lookup(scope)
        with connection.chunked_cursor() as cursor:
            cursor.itersize = ROW_FETCH_SIZE
            cursor.execute(sql, params)
            for concept_a, concept_b, evidence, score in cursor:
                yield concept_a, concept_b, evidence, float(score)


def _scoped_side_sql(value_sql, source_concept_ids, slice_predicate=""):
    """Return (sql, pairing_clause, params) for one side of a signal's self-join.

    With no source ids every pair is computed once, by keeping only the half of
    the join where the second id sorts higher. With source ids one side is
    pinned to them instead -- turning a scan of the whole corpus into a lookup
    of a handful of rows -- and the outer DISTINCT collapses the pair, which is
    then found from both directions.

    `slice_predicate` narrows the driving side to one slice of a corpus-wide
    search; see `_driving_side_slices`.

    A scheme scope is deliberately *not* applied here. Restricting the driving
    side to the scoped schemes as well as filtering after the join measured
    11.34s against 11.13s for the same slice and the same 24 rows: the planner
    already pushes the scope down, and saying it twice only adds a join.
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

    Every pair is found from its lower-id side, since the join only keeps
    `side_b > side_a`, so slicing on that side keeps each pair whole inside one
    slice and leaves the deduplication correct.

    Only the fuzzy signal is sliced. The exact signals join by equality, which
    Postgres answers with a hash join in seconds; slicing rebuilds that hash
    once per slice and measured 8x slower on the same data. The fuzzy signal
    probes an index per driving row instead, so the driving side is all that is
    re-scanned.

    A scoped search is already narrow enough to answer in one go.
    """
    if source_concept_ids is not None:
        return [""]
    return [
        # Masked rather than abs(): abs() of the one negative int4 with no
        # positive counterpart is an error. %% not %: parameters are always
        # passed, so psycopg would otherwise read the modulo as a placeholder.
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
    sql, scope_params = _pair_query(match_sql, scope, None)
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
    sql, scope_params = _pair_query(match_sql, scope, None)
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
            match_sql, scope, None, score_sql="matched.pair_score"
        )
        queries.append((sql, {**scope_params, **pushdown_params}))
    return queries


def _signal_queries(signal, scope, same_language_only):
    if signal == SIGNAL_SHARED_IDENTIFIER:
        return _shared_uri_pair_queries(scope)
    if signal == SIGNAL_EXACT_LABEL:
        return _exact_label_pair_queries(scope, same_language_only)
    return _similar_label_pair_queries(scope, same_language_only)


def find_exact_label_pairs(scope, same_language_only=True):
    """Concepts sharing a label, ignoring case and surrounding whitespace."""
    [(sql, params)] = _exact_label_pair_queries(scope, same_language_only)
    return _run_pair_query(sql, params, scope)


def find_shared_uri_pairs(scope):
    """Concepts carrying the same URI.

    A URI is globally meaningful, so two concepts sharing one are almost
    certainly the same concept.
    """
    [(sql, params)] = _shared_uri_pair_queries(scope)
    return _run_pair_query(sql, params, scope)


def find_similar_label_pairs(
    scope, similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD, same_language_only=True
):
    """Concepts whose labels are close without being identical.

    Backed by the `pg_trgm` GIN index on label content that migration 0012
    installs, using the `%` operator so the index does the filtering rather than
    a comparison per row.

    The threshold matters more than anything else here. Postgres defaults to
    0.3, which on a vocabulary the size of the AAT returns around 87 candidates
    per label -- noise rather than suggestion. At 0.7 it returns about 0.25.
    """
    for sql, params in _similar_label_pair_queries(scope, same_language_only):
        yield from _run_pair_query(
            sql, params, scope, similarity_threshold=similarity_threshold
        )


def _apply_trigram_session_tuning(similarity_threshold):
    """Tune the session for one fuzzy query, for the life of the transaction.

    SET LOCAL rather than SET: these revert when the transaction ends, so
    nothing leaks onto a connection Django may reuse.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SET LOCAL pg_trgm.similarity_threshold = %s", [similarity_threshold]
        )
        cursor.execute(
            f"SET LOCAL max_parallel_workers_per_gather = {TRIGRAM_PARALLEL_WORKERS}"
        )
        # The planner's default setup cost assumes parallelism rarely pays. Here
        # it always does -- every row drives an independent index probe -- so the
        # estimate is removed rather than argued with.
        cursor.execute("SET LOCAL parallel_setup_cost = 0")
        cursor.execute("SET LOCAL parallel_tuple_cost = 0")
        cursor.execute(f"SET LOCAL work_mem = '{TRIGRAM_WORK_MEM}'")


def _decided_pairs_sql():
    """Return (sql, params) for every pair already settled, in canonical order.

    A merge settles a pair, and so does an exactMatch -- which names the other
    concept by URI rather than by id, so it is resolved back through the URI
    tiles. Other match relations (close, broad, narrow, related) leave the pair
    open: the two may still be duplicates.
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
    """Run one pair query and store the pairs it finds, returning how many.

    The query is materialized with CREATE TABLE AS rather than read through a
    cursor, because Postgres never gives a declared cursor a parallel plan and
    the fuzzy signal is only affordable with its workers. The pairs then go
    straight into the candidate table without passing through Python, and the
    transaction commits here, so each query's results are visible as it ends.

    A pair already stored -- by a stronger signal, which runs first -- is left
    as it is, so the first reason a pair was found for is the one it keeps.
    """
    decided_sql, decided_params = _decided_pairs_sql()
    with transaction.atomic():
        if signal == SIGNAL_TRIGRAM:
            _apply_trigram_session_tuning(similarity_threshold)
        _prepare_scheme_lookup(scope)
        with connection.cursor() as cursor:
            # ON COMMIT DROP never fires inside an outer transaction; see
            # _prepare_scheme_lookup.
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


def find_decided_pairs():
    """Pairs an editor has already settled, in canonical order.

    A settled pair is not a suggestion -- it is a decision. Suggesting it again
    would put answered work back in the queue.
    """
    decided_sql, decided_params = _decided_pairs_sql()
    with connection.cursor() as cursor:
        cursor.execute(decided_sql, decided_params)
        return {(concept_a, concept_b) for concept_a, concept_b in cursor.fetchall()}


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


def restore_dismissed(run, user=None, candidate_ids=None):
    """Return dismissed pairs to the queue, returning (restored, left dismissed).

    Settling a pair only touches the runs where it is still pending, so a pair
    dismissed here and linked or merged since is still dismissed in this run.
    Restoring it would ask again about something already decided, so it stays.
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


def iter_candidates(
    scope,
    signals=EXACT_SIGNALS,
    same_language_only=True,
    similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD,
):
    """Yield every suggested pair, strongest signal first, without storing any.

    Signals can suggest the same pair for different reasons; they run strongest
    first, so the first mention of a pair is its best one.
    """
    validate_detection_options(signals, similarity_threshold)

    decided_pairs = find_decided_pairs()
    signal_sources = [
        (SIGNAL_SHARED_IDENTIFIER, lambda: find_shared_uri_pairs(scope)),
        (
            SIGNAL_EXACT_LABEL,
            lambda: find_exact_label_pairs(scope, same_language_only),
        ),
        (
            SIGNAL_TRIGRAM,
            lambda: find_similar_label_pairs(
                scope, similarity_threshold, same_language_only
            ),
        ),
    ]

    for signal, produce_pairs in signal_sources:
        if signal not in signals:
            continue
        for concept_a, concept_b, evidence, score in produce_pairs():
            if (concept_a, concept_b) in decided_pairs:
                continue
            yield concept_a, concept_b, signal, evidence, score


def collect_candidates(
    scope,
    signals=EXACT_SIGNALS,
    same_language_only=True,
    similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD,
):
    """`iter_candidates` as a {pair: (signal, evidence, score)} mapping.

    Only for scopes small enough to hold at once -- a single concept, a concept
    set. A whole-vocabulary run should be stored with `run_detection`.
    """
    candidates_by_pair = {}
    for concept_a, concept_b, signal, evidence, score in iter_candidates(
        scope, signals, same_language_only, similarity_threshold
    ):
        candidates_by_pair.setdefault((concept_a, concept_b), (signal, evidence, score))
    return candidates_by_pair


def _store_candidates(
    run, scope, signals, same_language_only, similarity_threshold, log
):
    """Store every signal's pairs, strongest first, returning how many landed.

    Each query commits on its own, so `candidate_count` climbs while the run is
    still going. Checking that the run still exists before each one is how a
    deleted run stops.
    """
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
    """Detect matches and store them as a reviewable run.

    `run` is an existing record to fill in, which is how the celery task reports
    against the run the request already returned to the caller.
    """
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
        # Deleting a run while a query is storing its pairs fails that query's
        # commit on the foreign key, which is a cancellation, not a failure.
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
