from django.db import models
from django.utils.translation import gettext as _

from arches_lingo.query_expressions import LevenshteinLessEqual


class LabelValueQuerySet(models.QuerySet):
    def fuzzy_search(self, term, max_edit_distance):
        from arches_lingo.models import VwLabelValue

        if len(term) > 255:
            raise ValueError(_("Fuzzy search terms cannot exceed 255 characters."))
        try:
            int(max_edit_distance)
        except ValueError:
            raise ValueError(_("Edit distance could not be converted to an integer."))

        fuzzy_matches = VwLabelValue.objects.annotate(
            edit_distance=LevenshteinLessEqual(
                models.F("value"),
                models.Value(term),
                models.Value(max_edit_distance),
                output_field=models.IntegerField(),
            )
        ).filter(edit_distance__lte=max_edit_distance)
        substring_matches = VwLabelValue.objects.filter(value__icontains=term).annotate(
            edit_distance=models.Value(0)
        )
        matches = substring_matches | fuzzy_matches

        return matches.order_by("edit_distance", "concept_id")
