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
import time

from django.conf import settings
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

SIGNAL_TRIGRAM = ConceptMatchCandidate.SIGNAL_TRIGRAM

EXACT_SIGNALS = (SIGNAL_SHARED_IDENTIFIER, SIGNAL_EXACT_LABEL)
ALL_SIGNALS = EXACT_SIGNALS + (SIGNAL_TRIGRAM,)

# Postgres defaults this to 0.3, which is far too loose for a vocabulary of any
# size; see find_similar_label_pairs.
DEFAULT_SIMILARITY_THRESHOLD = 0.7

# Comparing a vocabulary against itself is one index probe per label, each one
# CPU-bound on intersecting trigram posting lists and independent of the rest.
# Postgres allows two workers per gather by default, which leaves most of a
# server idle; measured 1.9x faster at eight on the AAT. Capped in practice by
# the server's own max_parallel_workers, so raising that is the deployment knob.
TRIGRAM_PARALLEL_WORKERS = getattr(settings, "LINGO_MATCH_PARALLEL_WORKERS", 8)

# Worth about 9% on the same measurement: enough of the bitmap stays exact to
# save some rechecks, but this is a distant second to parallelism.
TRIGRAM_WORK_MEM = getattr(settings, "LINGO_MATCH_WORK_MEM", "64MB")

CANDIDATE_BATCH_SIZE = 2_000

# How many rows a server-side cursor pulls at a time. Bounds how much of a
# result set is ever in memory at once.
ROW_FETCH_SIZE = 2_000

# How many independent queries a corpus-wide search is split into. More slices
# means results and progress arrive more often, at the cost of re-scanning the
# driving side once per slice -- cheap next to the index probes it drives.
MATCH_SLICE_COUNT = getattr(settings, "LINGO_MATCH_SLICE_COUNT", 16)

# How often a long-running search reports what it has found so far.
PROGRESS_INTERVAL_SECONDS = 10


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


def _run_pair_query(sql, params):
    """Yield rows as they arrive, rather than buffering the whole result.

    psycopg fetches everything on execute() with an ordinary cursor, so a
    corpus-wide run would hold every pair in memory before a single one was
    written. A server-side cursor keeps that bounded by `itersize`.
    """
    with transaction.atomic(), connection.chunked_cursor() as cursor:
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
    """Split a corpus-wide search into queries that each return as they finish.

    The outer query sorts in order to deduplicate, and a sort cannot emit its
    first row until it has consumed its last. One query over a whole vocabulary
    therefore stays silent for its entire run no matter how the rows are
    fetched -- which is why a 22-minute search reported nothing and then wrote
    every pair in under a tenth of a second.

    Slicing the driving side into independent queries gives back results, and
    progress, as each slice lands. Every pair is found from its lower-id side,
    since the join only keeps `side_b > side_a`, so slicing on that side keeps
    each pair whole inside one slice and leaves the deduplication correct.

    Only the fuzzy signal is sliced. The exact signals join by equality, which
    Postgres answers with a hash join in seconds; slicing rebuilds that hash
    once per slice and measured 8x slower on the same data. The fuzzy signal
    probes an index per driving row instead, so the driving side is all that is
    re-scanned and progress is nearly free.

    A scoped search is already narrow enough to answer in one go.
    """
    if source_concept_ids is not None:
        return [""]
    return [
        # %% not %: parameters are always passed, so psycopg would otherwise
        # read the modulo as a placeholder.
        f" AND abs(hashtext(scoped_side.concept_id::text)) %% {MATCH_SLICE_COUNT}"
        f" = {slice_index}"
        for slice_index in range(MATCH_SLICE_COUNT)
    ]


def find_exact_label_pairs(scope, same_language_only=True):
    """Concepts sharing a label, ignoring case and surrounding whitespace."""
    source_concept_ids = scope.resolve_source_concept_ids()
    language_clause = (
        " AND side_b.language IS NOT DISTINCT FROM side_a.language"
        if same_language_only
        else ""
    )

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
    See docs/concept-match-detection-plan.md for the measurements.
    """
    source_concept_ids = scope.resolve_source_concept_ids()
    language_clause = (
        " AND side_b.language IS NOT DISTINCT FROM side_a.language"
        if same_language_only
        else ""
    )

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
               {language_clause}
        """
        sql, scope_params = _pair_query(
            match_sql, scope, None, score_sql="matched.pair_score"
        )

        # SET LOCAL rather than SET: these are tuned for this one query and
        # revert when the transaction ends, so nothing leaks onto a reused
        # connection.
        with transaction.atomic():
            _apply_trigram_session_tuning(similarity_threshold)
            with connection.chunked_cursor() as cursor:
                cursor.itersize = ROW_FETCH_SIZE
                cursor.execute(sql, {**scope_params, **pushdown_params})
                for concept_a, concept_b, evidence, score in cursor:
                    yield concept_a, concept_b, evidence, float(score)


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


def iter_candidates(
    scope,
    signals=EXACT_SIGNALS,
    same_language_only=True,
    similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD,
):
    """Yield every suggested pair, strongest signal first.

    Signals can suggest the same pair for different reasons. Rather than hold
    every pair in memory to work out which reason wins, the signals are run
    strongest first and the writer drops a pair it has already stored -- so the
    first mention of a pair is its best one.

    Pairs are yielded rather than collected because a low threshold over a large
    vocabulary produces millions of them, and a dict of those, each carrying its
    evidence text, is far too much to hold before writing any.
    """
    unknown_signals = set(signals) - set(ALL_SIGNALS)
    if unknown_signals:
        raise ConceptMatchError(
            f"Unsupported signal(s): {', '.join(sorted(unknown_signals))}"
        )

    # Bounded by how much has already been decided, not by how much is found.
    decided_pairs = find_decided_pairs()

    # Ordered strongest first, so a pair found twice keeps the better reason.
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
    set. A whole-vocabulary run should go through `iter_candidates`.
    """
    candidates_by_pair = {}
    for concept_a, concept_b, signal, evidence, score in iter_candidates(
        scope, signals, same_language_only, similarity_threshold
    ):
        candidates_by_pair.setdefault((concept_a, concept_b), (signal, evidence, score))
    return candidates_by_pair


def _write_candidates(run, candidates, log=print):
    """Store candidates in batches as they are found, returning how many landed.

    Each batch is committed on its own rather than the whole run at once: a
    corpus-wide search runs for minutes, and holding every row for a single
    commit at the end is what made memory scale with the size of the result.

    Committing as it goes also means `candidate_count` climbs while the run is
    still going, which is what the interface reports as progress.

    `ignore_conflicts` does the deduplication. Signals run strongest first, so a
    pair already stored under a better reason is the one that survives -- the
    unique constraint on (run, concept_a, concept_b) settles it in the database
    rather than in a dictionary.
    """
    written_count = 0
    batch = []
    last_flush_at = time.monotonic()

    def flush():
        nonlocal written_count, batch, last_flush_at
        last_flush_at = time.monotonic()
        if not ConceptMatchRun.objects.filter(pk=run.pk).exists():
            raise ConceptMatchRunCancelled
        if not batch:
            # Still a sign of life, and the only one a run gets while it is
            # working through a stretch of labels that pair with nothing.
            ConceptMatchRun.objects.filter(pk=run.pk).update(
                last_progress=timezone.now()
            )
            return
        ConceptMatchCandidate.objects.bulk_create(batch, ignore_conflicts=True)
        # bulk_create with ignore_conflicts cannot report how many rows it
        # skipped, so the run's own rows are counted rather than the attempts.
        written_count = run.candidates.count()
        run.candidate_count = written_count
        run.last_progress = timezone.now()
        run.save(update_fields=["candidate_count", "last_progress"])
        log(f"  {written_count:,} candidate pairs so far")
        batch = []

    for concept_a, concept_b, signal, evidence, score in candidates:
        batch.append(
            ConceptMatchCandidate(
                run=run,
                concept_a_id=concept_a,
                concept_b_id=concept_b,
                score=score,
                signal=signal,
                evidence=evidence or "",
            )
        )
        # Flushed on size or on time: a slice of a large vocabulary can run for
        # a while and turn up only a handful of pairs, and waiting for a full
        # batch would leave the run looking stalled.
        if (
            len(batch) >= CANDIDATE_BATCH_SIZE
            or time.monotonic() - last_flush_at >= PROGRESS_INTERVAL_SECONDS
        ):
            flush()

    flush()
    return run.candidates.count()


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
        written_count = _write_candidates(
            run,
            iter_candidates(scope, signals, same_language_only, similarity_threshold),
            log=log,
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
