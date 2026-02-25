import uuid

from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models import models
from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_querysets.models import ResourceTileTree

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_TYPE_NODE,
    SCHEMES_GRAPH_ID,
)
from arches_lingo.utils.concept_builder import ConceptBuilder
from arches_lingo.views.api.edit_log import EDIT_TYPE_LABELS

PREF_LABEL_URI = "http://www.w3.org/2004/02/skos/core#prefLabel"


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class DashboardStatsView(View):
    def get(self, request):
        scheme_param = request.GET.get("scheme")
        scheme_id = None
        if scheme_param:
            try:
                scheme_id = str(uuid.UUID(scheme_param))
            except ValueError:
                return JSONErrorResponse(
                    title=_("Invalid scheme"),
                    message=_("scheme must be a valid UUID"),
                    status=400,
                )

        # --- Concept count ---
        Concept = ResourceTileTree.get_tiles("concept")
        if scheme_id:
            concept_count = Concept.filter(part_of_scheme__id=scheme_id).count()
        else:
            concept_count = models.ResourceInstance.objects.filter(
                graph_id=CONCEPTS_GRAPH_ID
            ).count()

        # --- Resource IDs for activity query ---
        if scheme_id:
            concept_ids = [
                str(pk)
                for pk in Concept.filter(part_of_scheme__id=scheme_id).values_list(
                    "pk", flat=True
                )
            ]
            all_resource_ids = concept_ids + [scheme_id]
        else:
            concept_ids = [
                str(pk)
                for pk in models.ResourceInstance.objects.filter(
                    graph_id=CONCEPTS_GRAPH_ID
                ).values_list("pk", flat=True)
            ]
            scheme_ids = [
                str(pk)
                for pk in models.ResourceInstance.objects.filter(
                    graph_id=SCHEMES_GRAPH_ID
                ).values_list("pk", flat=True)
            ]
            all_resource_ids = concept_ids + scheme_ids

        # --- Build resource name and type lookup ---
        resource_instances = models.ResourceInstance.objects.filter(
            resourceinstanceid__in=all_resource_ids
        )
        name_map = {}
        type_map = {}
        for ri in resource_instances:
            descriptors = ri.descriptors or {}
            name_map[str(ri.resourceinstanceid)] = next(
                (v.get("name", "") for v in descriptors.values() if v.get("name")),
                "",
            )
            type_map[str(ri.resourceinstanceid)] = (
                "scheme" if str(ri.graph_id) == str(SCHEMES_GRAPH_ID) else "concept"
            )

        # --- Recent activity: 20 most recent edits, deduplicated by transaction ---
        edits = models.EditLog.objects.filter(
            resourceinstanceid__in=all_resource_ids
        ).order_by("-timestamp")[:100]

        seen_transactions = set()
        activity = []
        for edit in edits:
            key = str(edit.transactionid) if edit.transactionid else str(edit.editlogid)
            if key not in seen_transactions:
                seen_transactions.add(key)
                activity.append(
                    {
                        "editlogid": str(edit.editlogid),
                        "edittype_label": _(
                            EDIT_TYPE_LABELS.get(edit.edittype, edit.edittype)
                        ),
                        "timestamp": (
                            edit.timestamp.isoformat() if edit.timestamp else None
                        ),
                        "user_username": edit.user_username,
                        "user_firstname": edit.user_firstname,
                        "user_lastname": edit.user_lastname,
                        "resource_id": edit.resourceinstanceid,
                        "resource_name": name_map.get(edit.resourceinstanceid, ""),
                        "resource_type": type_map.get(
                            edit.resourceinstanceid, "concept"
                        ),
                    }
                )
            if len(activity) >= 20:
                break

        return JSONResponse(
            {
                "concept_count": concept_count,
                "recent_activity": activity,
            }
        )


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class MissingTranslationsView(View):
    def get(self, request):
        language_code = request.GET.get("language")
        if not language_code:
            return JSONErrorResponse(
                title=_("Missing parameter"),
                message=_("language parameter is required"),
                status=400,
            )

        scheme_param = request.GET.get("scheme")
        scheme_id = None
        if scheme_param:
            try:
                scheme_id = str(uuid.UUID(scheme_param))
            except ValueError:
                return JSONErrorResponse(
                    title=_("Invalid scheme"),
                    message=_("scheme must be a valid UUID"),
                    status=400,
                )

        page_number = int(request.GET.get("page", 1))
        items_per_page = int(request.GET.get("items", 25))

        # Find concept IDs that have a preferred label in the given language
        concepts_with_pref_ids = set(
            models.TileModel.objects.filter(
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                data__contains={
                    CONCEPT_NAME_LANGUAGE_NODE: language_code,
                    CONCEPT_NAME_TYPE_NODE: [{"uri": PREF_LABEL_URI}],
                },
            ).values_list("resourceinstance_id", flat=True)
        )

        # All concept IDs, optionally filtered by scheme
        Concept = ResourceTileTree.get_tiles("concept")
        if scheme_id:
            all_concept_ids = list(
                Concept.filter(part_of_scheme__id=scheme_id).values_list(
                    "pk", flat=True
                )
            )
        else:
            all_concept_ids = list(
                models.ResourceInstance.objects.filter(
                    graph_id=CONCEPTS_GRAPH_ID
                ).values_list("resourceinstanceid", flat=True)
            )

        # Concepts missing preferred label in given language
        missing_ids = [
            str(pk) for pk in all_concept_ids if pk not in concepts_with_pref_ids
        ]
        missing_ids.sort()

        paginator = Paginator(missing_ids, items_per_page)
        page = paginator.get_page(page_number)
        total_results = paginator.count

        data = []
        if total_results:
            page_ids = list(page.object_list)
            builder = ConceptBuilder(page_ids, include_parents=True)
            data = [
                builder.serialize_concept(concept_id, parents=True, children=False)
                for concept_id in page_ids
            ]

        return JSONResponse(
            {
                "current_page": page.number,
                "total_pages": paginator.num_pages,
                "results_per_page": paginator.per_page,
                "total_results": total_results,
                "data": data,
            }
        )
