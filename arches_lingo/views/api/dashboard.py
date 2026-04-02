from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models import models
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.const import SCHEMES_GRAPH_ID
from arches_lingo.mixins.permissions import AnonymousAccessMixin
from arches_lingo.utils.dashboard import (
    attach_activity_labels,
    build_recent_activity,
    get_all_scheme_ids,
    get_concept_ids,
    get_concept_type_breakdown,
    get_label_stats,
    parse_days_param,
    parse_scheme_ids,
)


class DashboardStatsView(AnonymousAccessMixin, View):
    def get(self, request):
        try:
            scheme_ids = parse_scheme_ids(request)
        except ValueError as error:
            return JSONErrorResponse(
                title=_("Invalid scheme"),
                message=str(error),
                status=400,
            )

        user = request.user
        user_display_name = (
            user.first_name or user.username if user.is_authenticated else ""
        )

        total_scheme_count = models.ResourceInstance.objects.filter(
            graph_id=SCHEMES_GRAPH_ID
        ).count()
        scheme_count = len(scheme_ids) if scheme_ids else total_scheme_count

        concept_count, concept_qs = get_concept_ids(scheme_ids)

        resolved_scheme_ids = scheme_ids or get_all_scheme_ids()

        try:
            activity_cutoff = parse_days_param(request)
        except ValueError as error:
            return JSONErrorResponse(
                title=_("Invalid parameter"),
                message=str(error),
                status=400,
            )

        recent_activity = build_recent_activity(
            concept_qs, resolved_scheme_ids, activity_cutoff
        )
        attach_activity_labels(recent_activity)

        concepts_by_type = get_concept_type_breakdown(concept_qs, concept_count)
        label_count, labels_by_type, labels_by_language = get_label_stats(concept_qs)

        labels_per_concept = (
            round(label_count / concept_count, 1) if concept_count else 0
        )

        return JSONResponse(
            {
                "user_display_name": user_display_name,
                "scheme_count": scheme_count,
                "concept_count": concept_count,
                "concepts_by_type": concepts_by_type,
                "label_count": label_count,
                "labels_per_concept": labels_per_concept,
                "labels_by_type": labels_by_type,
                "labels_by_language": labels_by_language,
                "recent_activity": recent_activity,
            }
        )
