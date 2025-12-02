from django.db.models import Min, Case, When, Value, IntegerField
from django.db.models.functions import Lower

from arches.app.models.system_settings import settings
from arches_lingo.querysets import fuzzy_search


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

    ranked_tiles = fuzzy_tiles.annotate(
        text_rank=Case(
            When(
                appellative_status_ascribed_name_content__iexact=term,
                then=Value(0),
            ),
            When(
                appellative_status_ascribed_name_content__istartswith=term,
                then=Value(1),
            ),
            When(
                appellative_status_ascribed_name_content__icontains=term,
                then=Value(2),
            ),
            default=Value(3),
            output_field=IntegerField(),
        )
    )

    base_query = ranked_tiles.values("resourceinstance").annotate(
        best_text_rank=Min("text_rank"),
        best_label_rank=Min("label_rank"),
        sort_label=Min(Lower("appellative_status_ascribed_name_content")),
    )

    if order_mode == "alphabetical":
        ordered_query = base_query.order_by("sort_label", "resourceinstance")
    elif order_mode == "reverse-alphabetical":
        ordered_query = base_query.order_by("-sort_label", "resourceinstance")
    else:
        ordered_query = base_query.order_by(
            "best_text_rank",
            "best_label_rank",
            "resourceinstance",
        )

    return ordered_query.values_list("resourceinstance", flat=True)


def build_concept_ids_for_non_fuzzy(labels_queryset, order_mode):
    base_query = labels_queryset.values("resourceinstance").annotate(
        sort_label=Min(Lower("appellative_status_ascribed_name_content")),
    )

    if order_mode == "alphabetical":
        ordered_query = base_query.order_by("sort_label", "resourceinstance")
    elif order_mode == "reverse-alphabetical":
        ordered_query = base_query.order_by("-sort_label", "resourceinstance")
    else:
        ordered_query = base_query.order_by("resourceinstance")

    return ordered_query.values_list("resourceinstance", flat=True)
