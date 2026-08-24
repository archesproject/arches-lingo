from django.db import models
from django.db.models import Case, When, Value, IntegerField, Q
from django.db.models.functions import Left
from django.utils.translation import gettext as _

from arches_lingo.query_expressions import LevenshteinLessEqual


def fuzzy_search(queryset, term, max_edit_distance):
    if len(term) > 255:
        raise ValueError(_("Fuzzy search terms cannot exceed 255 characters."))

    try:
        max_edit_distance = int(max_edit_distance)
    except ValueError:
        raise ValueError(_("Edit distance could not be converted to an integer."))

    label_rank = Case(
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

    if max_edit_distance == 0:
        # No fuzzy matching needed — skip levenshtein entirely.
        return queryset.annotate(label_rank=label_rank).filter(
            appellative_status_ascribed_name_content__icontains=term
        )

    # Truncate values to 255 chars for levenshtein to avoid the PostgreSQL
    # "levenshtein argument exceeds maximum length of 255 characters" error.
    # The icontains filter still matches against the full value.
    matches = queryset.annotate(
        edit_distance=LevenshteinLessEqual(
            Left(models.F("appellative_status_ascribed_name_content"), 255),
            models.Value(term),
            models.Value(max_edit_distance),
            output_field=models.IntegerField(),
        ),
        label_rank=label_rank,
    ).filter(
        Q(edit_distance__lte=max_edit_distance)
        | Q(appellative_status_ascribed_name_content__icontains=term)
    )

    return matches
