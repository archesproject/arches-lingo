from django.db import models
from django.db.models import Case, When, Value, IntegerField, Q
from django.utils.translation import gettext as _

from arches_lingo.query_expressions import LevenshteinLessEqual


def fuzzy_search(queryset, term, max_edit_distance):
    if len(term) > 255:
        raise ValueError(_("Fuzzy search terms cannot exceed 255 characters."))

    try:
        max_edit_distance = int(max_edit_distance)
    except ValueError:
        raise ValueError(_("Edit distance could not be converted to an integer."))

    matches = queryset.annotate(
        edit_distance=LevenshteinLessEqual(
            models.F("appellative_status_ascribed_name_content"),
            models.Value(term),
            models.Value(max_edit_distance),
            output_field=models.IntegerField(),
        ),
        label_rank=Case(
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
        ),
    ).filter(
        Q(edit_distance__lte=max_edit_distance)
        | Q(appellative_status_ascribed_name_content__icontains=term)
    )

    return matches
