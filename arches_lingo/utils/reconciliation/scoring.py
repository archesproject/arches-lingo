"""Turn SearchResultSet ranks into 0–100 reconciliation scores.

``best_rank`` is ``tier * 1000 + language_preference``; the tiers come from
``SearchResultSet._build_search_sql`` and run from 0 (prefLabel exact) to 7
(trigram similarity only).
"""

PREF_LABEL_EXACT_TIER = 0
ALT_LABEL_EXACT_TIER = 1

SCORE_BY_TIER = {
    PREF_LABEL_EXACT_TIER: 100,
    ALT_LABEL_EXACT_TIER: 90,
    2: 70,  # prefLabel prefix
    3: 60,  # prefLabel contains
    4: 55,  # altLabel prefix, or any other label type exact
    5: 45,  # altLabel contains, or any label prefix
    6: 35,  # any label contains
    7: 0,  # trigram similarity only
}
# Concepts found only by identifier or exactMatch, never by label.
NO_LABEL_MATCH_TIER = 8
# Keeps a fuzzy match from ever outscoring an exact label.
MAX_SIMILARITY_SCORE = 80
IDENTIFIED_SCORE = 100
PROPERTY_MATCH_BOOST = 10
PROPERTY_CONTRADICTION_PENALTY = 30


def tier_from_rank(best_rank):
    return best_rank // 1000


def score_match(best_rank, best_similarity):
    tier = tier_from_rank(best_rank)
    tier_score = SCORE_BY_TIER.get(tier, 0)
    if tier <= ALT_LABEL_EXACT_TIER:
        return tier_score
    similarity_score = round((best_similarity or 0) * MAX_SIMILARITY_SCORE)
    return max(tier_score, similarity_score)


def adjust_score_for_properties(score, matched_property_count, is_contradicted):
    adjusted_score = score + matched_property_count * PROPERTY_MATCH_BOOST
    if is_contradicted:
        adjusted_score -= PROPERTY_CONTRADICTION_PENALTY
    return max(0, min(100, adjusted_score))


def decide_automatic_match(scored_candidates):
    """Return the one candidate safe for OpenRefine to auto-match, or None.

    A unique identifier or exactMatch hit wins outright; otherwise only an
    unambiguous prefLabel exact match qualifies, in the query's language when it
    names one. Candidates a query property
    contradicts drop out first, so a broader term can settle a homograph. A
    retired concept, or one standing in for a merged concept, never auto-matches,
    since the editor should see it.
    """
    plausible_candidates = [
        candidate for candidate in scored_candidates if not candidate.is_contradicted
    ]
    shortlist = [
        candidate for candidate in plausible_candidates if candidate.is_identified
    ] or [
        candidate
        for candidate in plausible_candidates
        if candidate.tier == PREF_LABEL_EXACT_TIER
        and not candidate.is_other_language_match
    ]
    if len(shortlist) != 1:
        return None
    only_candidate = shortlist[0]
    if (
        only_candidate.substitutes_for_concept_id is not None
        or only_candidate.is_retired
    ):
        return None
    return only_candidate
