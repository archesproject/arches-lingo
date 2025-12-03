from django.db.models import Min
from django.db.models.functions import Lower

from arches.app.models.system_settings import settings
from arches_lingo.querysets import fuzzy_search
from arches_lingo.utils.concept_builder import ConceptBuilder


ORDER_MODE_ALPHABETICAL = "alphabetical"
ORDER_MODE_REVERSE_ALPHABETICAL = "reverse-alphabetical"
ORDER_MODE_UNSORTED = "unsorted"

VALUETYPE_PREF_LABEL = "prefLabel"
VALUETYPE_ALT_LABEL = "altLabel"
VALUETYPE_OTHER = "other"

MAX_MATCH_RANK = 7
MAX_LANGUAGE_RANK = 2
MAX_LABEL_RANK = 0
WORST_SCORE = (MAX_MATCH_RANK, MAX_LANGUAGE_RANK, MAX_LABEL_RANK, "\uffff")

# text_match_rank indices:
# 0 = exact, 1 = prefix, 2 = substring, 3 = no match
MATCH_RANK_TABLE = {
    VALUETYPE_PREF_LABEL: (0, 2, 3, 6),
    VALUETYPE_ALT_LABEL: (1, 4, 5, 6),
    VALUETYPE_OTHER: (4, 5, 6, 7),
}


def resolve_max_edit_distance(term):
    elastic_prefix_length = settings.SEARCH_TERM_SENSITIVITY

    if elastic_prefix_length <= 0:
        base_max_edit_distance = 5
    elif elastic_prefix_length >= 5:
        base_max_edit_distance = 0
    else:
        base_max_edit_distance = int(5 - elastic_prefix_length)

    if not term:
        return base_max_edit_distance

    term_length = len(term)

    if term_length <= 3:
        return 0

    if term_length <= 5:
        return min(base_max_edit_distance, 1)

    return min(base_max_edit_distance, 2)


def build_ranked_concept_ids_for_term(
    labels,
    term,
    max_edit_distance,
    order_mode,
):
    fuzzy_tiles = fuzzy_search(labels, term, max_edit_distance)

    concept_identifiers_in_fuzzy_order = []
    seen_concept_identifiers = set()

    for concept_identifier in fuzzy_tiles.values_list("resourceinstance", flat=True):
        if concept_identifier not in seen_concept_identifiers:
            seen_concept_identifiers.add(concept_identifier)
            concept_identifiers_in_fuzzy_order.append(concept_identifier)

    if order_mode == ORDER_MODE_UNSORTED:
        return concept_identifiers_in_fuzzy_order

    labeled_concepts = (
        labels.filter(resourceinstance__in=concept_identifiers_in_fuzzy_order)
        .values("resourceinstance")
        .annotate(
            sort_label=Min(Lower("appellative_status_ascribed_name_content")),
        )
    )

    sort_label_by_concept_identifier = {
        labeled_concept["resourceinstance"]: labeled_concept["sort_label"]
        for labeled_concept in labeled_concepts
    }

    concept_identifiers_in_fuzzy_order.sort(
        key=lambda concept_identifier: sort_label_by_concept_identifier.get(
            concept_identifier,
            "",
        ),
        reverse=(order_mode == ORDER_MODE_REVERSE_ALPHABETICAL),
    )

    return concept_identifiers_in_fuzzy_order


def build_concept_ids_for_non_fuzzy(labels_queryset, order_mode):
    base_query = labels_queryset.values("resourceinstance").annotate(
        sort_label=Min(Lower("appellative_status_ascribed_name_content")),
    )

    if order_mode == ORDER_MODE_ALPHABETICAL:
        ordered_query = base_query.order_by("sort_label", "resourceinstance")
    elif order_mode == ORDER_MODE_REVERSE_ALPHABETICAL:
        ordered_query = base_query.order_by("-sort_label", "resourceinstance")
    else:
        ordered_query = base_query.order_by("resourceinstance")

    return ordered_query.values_list("resourceinstance", flat=True)


def score_concept_for_term(
    concept_data,
    search_term,
    active_language,
    system_language,
):
    search_term_lower = (search_term or "").lower()
    best_score = WORST_SCORE

    for label_data in concept_data.get("labels", []):
        raw_label_value = label_data.get("value") or ""
        label_value_lower = raw_label_value.lower()

        if not search_term_lower:
            text_match_rank = 3
        elif label_value_lower == search_term_lower:
            text_match_rank = 0
        elif label_value_lower.startswith(search_term_lower):
            text_match_rank = 1
        elif search_term_lower in label_value_lower:
            text_match_rank = 2
        else:
            text_match_rank = 3

        label_language_identifier = label_data.get("language_id")
        if label_language_identifier == active_language:
            language_rank = 0
        elif label_language_identifier == system_language:
            language_rank = 1
        else:
            language_rank = 2

        raw_label_rank = label_data.get("rank")
        if isinstance(raw_label_rank, int):
            label_rank = -raw_label_rank
        else:
            label_rank = 0

        valuetype = label_data.get("valuetype_id") or VALUETYPE_OTHER
        match_ranks_for_type = MATCH_RANK_TABLE.get(
            valuetype, MATCH_RANK_TABLE[VALUETYPE_OTHER]
        )
        match_rank = match_ranks_for_type[text_match_rank]

        label_score = (
            match_rank,
            language_rank,
            label_rank,
            label_value_lower,
        )

        if label_score < best_score:
            best_score = label_score

    return best_score


def rank_concepts_for_unsorted_term(
    concept_identifiers,
    search_term,
    active_language,
    system_language,
):
    concept_builder = ConceptBuilder()

    scored_concepts = []
    for concept_index, concept_identifier in enumerate(concept_identifiers):
        concept_data = concept_builder.serialize_concept(
            str(concept_identifier),
            parents=True,
            children=False,
        )
        concept_score = score_concept_for_term(
            concept_data,
            search_term,
            active_language,
            system_language,
        )
        scored_concepts.append(
            (concept_score, concept_index, concept_data),
        )

    scored_concepts.sort(
        key=lambda scored_entry: (
            scored_entry[0],
            scored_entry[1],
        )
    )

    ordered_concepts = [scored_entry[2] for scored_entry in scored_concepts]
    return ordered_concepts
