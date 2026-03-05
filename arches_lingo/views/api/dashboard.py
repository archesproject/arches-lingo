import uuid

from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models import models
from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONResponse

from arches_lingo.const import SCHEMES_GRAPH_ID
from arches_lingo.utils.dashboard import (
    attach_activity_labels,
    build_recent_activity,
    build_resource_type_map,
    get_all_scheme_ids,
    get_concept_ids,
    get_concept_type_breakdown,
    get_label_stats,
    parse_days_param,
    parse_scheme_ids,
)


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class DashboardStatsView(View):
    def get(self, request):
        scheme_ids, error = parse_scheme_ids(request)
        if error:
            return error

        user = request.user
        user_display_name = (
            user.first_name or user.username if user.is_authenticated else ""
        )

        total_scheme_count = models.ResourceInstance.objects.filter(
            graph_id=SCHEMES_GRAPH_ID
        ).count()
        scheme_count = len(scheme_ids) if scheme_ids else total_scheme_count

        concept_count, concept_ids_list = get_concept_ids(scheme_ids)

        resolved_scheme_ids = scheme_ids or get_all_scheme_ids()
        all_resource_ids = concept_ids_list + resolved_scheme_ids

        type_map = build_resource_type_map(all_resource_ids)

        since, error = parse_days_param(request)
        if error:
            return error

        activity = build_recent_activity(all_resource_ids, type_map, since)
        attach_activity_labels(activity)

        concept_uuids = [uuid.UUID(rid) for rid in concept_ids_list]
        concepts_by_type = get_concept_type_breakdown(concept_uuids)
        label_count, labels_by_type, labels_by_language = get_label_stats(concept_uuids)

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
                "recent_activity": activity,
            }
        )
