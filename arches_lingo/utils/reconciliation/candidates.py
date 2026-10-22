import json
from dataclasses import dataclass, field, replace

from django.conf import settings
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from arches_lingo.utils.concept_lifecycle import RETIRED_STATE_ID
from arches_lingo.utils.concepts import (
    ORDER_MODE_UNSORTED,
    build_search_queryset,
    resolve_max_edit_distance,
)
from arches_lingo.utils.reconciliation.concept_summaries import (
    get_lifecycle_state_ids,
    summarize_concepts,
)
from arches_lingo.utils.reconciliation.query_properties import (
    ALT_LABEL,
    BROADER,
    INCLUDE_RETIRED,
    LANGUAGE,
    PropertyEvidence,
    evaluate_query_properties,
    find_identified_concept_ids,
    gather_property_evidence,
    is_true_value,
    parse_query_properties,
)
from arches_lingo.utils.reconciliation.scoring import (
    IDENTIFIED_SCORE,
    NO_LABEL_MATCH_TIER,
    adjust_score_for_properties,
    decide_automatic_match,
    score_match,
    tier_from_rank,
)
from arches_lingo.utils.reconciliation.visibility import (
    RECONCILABLE_LIFECYCLE_STATE_IDS,
    SEARCHED_LIFECYCLE_STATE_IDS,
    reconcilable_scheme_ids,
    resolve_merge_survivors,
)

MAX_QUERIES_PER_REQUEST = 50
DEFAULT_CANDIDATE_LIMIT = 10
MAX_CANDIDATE_LIMIT = 25
MAX_QUERY_LENGTH = 255
# Retired matches are searched but mostly dropped, so fetch extra to still fill
# the requested limit afterwards.
OVERFETCH_FACTOR = 2
# Properties can only re-rank what the label search returned, so a query using
# them searches a wider window for the property to promote from.
RERANKING_SEARCH_WINDOW = MAX_CANDIDATE_LIMIT * OVERFETCH_FACTOR


@dataclass(frozen=True)
class ReconciliationQuery:
    text: str
    scheme_id: str | None
    limit: int
    property_values: dict = field(default_factory=dict)

    def values_for(self, property_id):
        return self.property_values.get(property_id, ())

    @property
    def language(self):
        languages = self.values_for(LANGUAGE)
        return languages[0] if languages else None

    @property
    def include_retired(self):
        return is_true_value(self.values_for(INCLUDE_RETIRED))

    @property
    def search_window(self):
        if self.values_for(BROADER) or self.values_for(ALT_LABEL):
            return RERANKING_SEARCH_WINDOW
        return self.limit * OVERFETCH_FACTOR


@dataclass(frozen=True)
class ScoredCandidate:
    concept_id: str
    tier: int
    score: int
    substitutes_for_concept_id: str | None = None
    is_identified: bool = False
    is_contradicted: bool = False
    is_retired: bool = False


def parse_reconciliation_queries(raw_queries, default_scheme_id=None):
    """Validate a W3C reconciliation ``queries`` batch; raise ValueError if malformed."""
    try:
        raw_queries_by_key = json.loads(raw_queries)
    except (TypeError, ValueError):
        raise ValueError(_("The queries parameter must be a JSON object."))
    if not isinstance(raw_queries_by_key, dict):
        raise ValueError(_("The queries parameter must be a JSON object."))
    if len(raw_queries_by_key) > MAX_QUERIES_PER_REQUEST:
        raise ValueError(
            _("At most %(limit)s queries can be sent at once.")
            % {"limit": MAX_QUERIES_PER_REQUEST}
        )
    return {
        query_key: parse_reconciliation_query(raw_query, default_scheme_id)
        for query_key, raw_query in raw_queries_by_key.items()
    }


def parse_reconciliation_query(raw_query, default_scheme_id):
    if not isinstance(raw_query, dict):
        raise ValueError(_("Each query must be a JSON object."))

    query_text = raw_query.get("query")
    if not isinstance(query_text, str) or not query_text.strip():
        raise ValueError(_('Each query needs a non-empty "query" string.'))
    query_text = query_text.strip()
    if len(query_text) > MAX_QUERY_LENGTH:
        raise ValueError(
            _("Queries cannot exceed %(limit)s characters.")
            % {"limit": MAX_QUERY_LENGTH}
        )

    scheme_id = raw_query.get("type", default_scheme_id)
    # Version 0.1 of the API allows a list of types.
    if isinstance(scheme_id, list) and len(scheme_id) == 1:
        scheme_id = scheme_id[0]
    if scheme_id is not None and not isinstance(scheme_id, str):
        raise ValueError(_("Each query may name at most one type."))

    limit = raw_query.get("limit", DEFAULT_CANDIDATE_LIMIT)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError(_('A query "limit" must be a positive integer.'))

    return ReconciliationQuery(
        text=query_text,
        scheme_id=scheme_id,
        limit=min(limit, MAX_CANDIDATE_LIMIT),
        property_values=parse_query_properties(raw_query.get("properties")),
    )


def find_scored_candidates(query, searchable_scheme_ids, identified_concept_ids):
    if query.scheme_id is None:
        scheme_ids = searchable_scheme_ids
    elif query.scheme_id in searchable_scheme_ids:
        scheme_ids = {query.scheme_id}
    else:
        return []

    search = build_search_queryset(
        None,
        query.text,
        resolve_max_edit_distance(query.text),
        ORDER_MODE_UNSORTED,
        query.language or get_language() or settings.LANGUAGE_CODE,
        settings.LANGUAGE_CODE,
        scheme_ids=scheme_ids,
        lifecycle_state_ids=SEARCHED_LIFECYCLE_STATE_IDS,
    )
    scored_candidates = [
        ScoredCandidate(
            concept_id=concept_id,
            tier=tier_from_rank(best_rank),
            score=score_match(best_rank, best_similarity),
        )
        for concept_id, best_rank, best_similarity in search.scored_slice(
            query.search_window
        )
    ]

    label_matched_ids = {candidate.concept_id for candidate in scored_candidates}
    scored_candidates = [
        (
            replace(candidate, score=IDENTIFIED_SCORE, is_identified=True)
            if candidate.concept_id in identified_concept_ids
            else candidate
        )
        for candidate in scored_candidates
    ]
    # Sorted so results are deterministic; scheme scope is applied with the others.
    for concept_id in sorted(identified_concept_ids - label_matched_ids):
        scored_candidates.append(
            ScoredCandidate(
                concept_id=concept_id,
                tier=NO_LABEL_MATCH_TIER,
                score=IDENTIFIED_SCORE,
                is_identified=True,
            )
        )
    return scored_candidates


def expand_retired_candidates(
    query, scored_candidates, survivor_by_retired_id, retired_ids
):
    """Swap each retired candidate for its merge survivor, if any, and keep the
    retired concept itself only when the query asks for retired concepts."""
    expanded_candidates = []
    for candidate in scored_candidates:
        if candidate.concept_id not in retired_ids:
            expanded_candidates.append(candidate)
            continue
        survivor_id = survivor_by_retired_id.get(candidate.concept_id)
        if survivor_id is not None:
            expanded_candidates.append(
                replace(
                    candidate,
                    concept_id=survivor_id,
                    substitutes_for_concept_id=candidate.concept_id,
                    is_identified=False,
                )
            )
        if query.include_retired:
            expanded_candidates.append(replace(candidate, is_retired=True))
    return expanded_candidates


def is_better_candidate(candidate, existing_candidate):
    if existing_candidate is None or candidate.score > existing_candidate.score:
        return True
    # On a tie, a direct match beats a concept standing in for a merged one.
    return (
        candidate.score == existing_candidate.score
        and existing_candidate.substitutes_for_concept_id is not None
        and candidate.substitutes_for_concept_id is None
    )


def describe_candidate(summary, candidate):
    if not candidate.is_retired:
        return summary
    return {
        **summary,
        "description": _("%(description)s (retired)")
        % {"description": summary["description"]},
    }


def build_query_results(query, expanded_candidates, summaries, evidence_by_concept_id):
    best_candidate_by_concept_id = {}
    for candidate in expanded_candidates:
        summary = summaries.get(candidate.concept_id)
        if summary is None:
            continue
        if query.scheme_id and summary["type"][0]["id"] != query.scheme_id:
            continue

        matched_property_count, is_contradicted = evaluate_query_properties(
            query,
            evidence_by_concept_id.get(candidate.concept_id, PropertyEvidence()),
            candidate.is_identified,
        )
        candidate = replace(
            candidate,
            score=adjust_score_for_properties(
                candidate.score, matched_property_count, is_contradicted
            ),
            is_contradicted=is_contradicted,
        )
        if is_better_candidate(
            candidate, best_candidate_by_concept_id.get(candidate.concept_id)
        ):
            best_candidate_by_concept_id[candidate.concept_id] = candidate

    # A stable sort keeps the search's own ordering between equal scores.
    ranked_candidates = sorted(
        best_candidate_by_concept_id.values(),
        key=lambda candidate: -candidate.score,
    )[: query.limit]
    automatic_match = decide_automatic_match(ranked_candidates)
    return [
        {
            "id": candidate.concept_id,
            **describe_candidate(summaries[candidate.concept_id], candidate),
            "score": candidate.score,
            "match": candidate is automatic_match,
        }
        for candidate in ranked_candidates
    ]


def reconcile_queries(raw_queries, default_scheme_id=None):
    """Answer a reconciliation batch with ``{key: {"result": [...]}}``.

    Lookups after the per-query searches are shared by the whole batch, so the
    query count grows with the number of queries, not the number of candidates.
    """
    queries_by_key = parse_reconciliation_queries(raw_queries, default_scheme_id)
    searchable_scheme_ids = reconcilable_scheme_ids()
    identified_concept_ids_by_key = find_identified_concept_ids(queries_by_key)
    scored_candidates_by_key = {
        query_key: find_scored_candidates(
            query, searchable_scheme_ids, identified_concept_ids_by_key[query_key]
        )
        for query_key, query in queries_by_key.items()
    }

    found_concept_ids = {
        candidate.concept_id
        for scored_candidates in scored_candidates_by_key.values()
        for candidate in scored_candidates
    }
    lifecycle_state_id_by_concept_id = get_lifecycle_state_ids(found_concept_ids)
    retired_ids = {
        concept_id
        for concept_id in found_concept_ids
        if lifecycle_state_id_by_concept_id.get(concept_id) == RETIRED_STATE_ID
    }
    survivor_by_retired_id = resolve_merge_survivors(retired_ids)

    survivor_ids = set(survivor_by_retired_id.values()) - found_concept_ids
    lifecycle_state_id_by_concept_id.update(get_lifecycle_state_ids(survivor_ids))
    reconcilable_concept_ids = {
        concept_id
        for concept_id in (found_concept_ids | survivor_ids) - retired_ids
        if lifecycle_state_id_by_concept_id.get(concept_id)
        in RECONCILABLE_LIFECYCLE_STATE_IDS
    }
    # Identifier and exactMatch hits skip the search's lifecycle filter, so a draft
    # found that way is only kept out here, by never being summarized.
    if any(query.include_retired for query in queries_by_key.values()):
        reconcilable_concept_ids |= retired_ids

    summaries_by_language = {
        language: summarize_concepts(reconcilable_concept_ids, language)
        for language in {query.language for query in queries_by_key.values()}
    }
    evidence_by_concept_id = gather_property_evidence(
        reconcilable_concept_ids,
        needs_broader=any(
            query.values_for(BROADER) for query in queries_by_key.values()
        ),
        needs_alternate_labels=any(
            query.values_for(ALT_LABEL) for query in queries_by_key.values()
        ),
    )

    return {
        query_key: {
            "result": build_query_results(
                query,
                expand_retired_candidates(
                    query,
                    scored_candidates_by_key[query_key],
                    survivor_by_retired_id,
                    retired_ids,
                ),
                summaries_by_language[query.language],
                evidence_by_concept_id,
            )
        }
        for query_key, query in queries_by_key.items()
    }
