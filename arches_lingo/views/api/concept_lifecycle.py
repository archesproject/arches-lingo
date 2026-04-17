from http import HTTPStatus

from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models.models import ResourceInstance, TileModel
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.const import (
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
)
from arches_lingo.mixins.permissions import LingoEditorMixin
from arches_lingo.utils.concept_lifecycle import (
    EDITING_STATE_ID,
    RETIRED_STATE_ID,
    VALID_STRATEGIES,
    get_narrower_ids,
    retire_concept,
    unretire_concept,
)


class ConceptRetireView(LingoEditorMixin, View):
    def post(self, request, pk):
        try:
            concept = ResourceInstance.objects.get(pk=pk)
        except ResourceInstance.DoesNotExist:
            return JSONErrorResponse(
                title=_("Not found"),
                message=_("Concept not found."),
                status=HTTPStatus.NOT_FOUND,
            )

        strategy = request.GET.get("strategy")

        if get_narrower_ids(str(pk)) and strategy not in VALID_STRATEGIES:
            return JSONErrorResponse(
                title=_("Strategy required"),
                message=_(
                    "This concept has children. Provide a strategy: "
                    "reparent, delete_children, or orphan."
                ),
                status=HTTPStatus.BAD_REQUEST,
            )

        with transaction.atomic():
            retire_concept(concept, strategy)

        return JSONResponse({"retired": True})


class ConceptUnretireView(LingoEditorMixin, View):
    def post(self, request, pk):
        try:
            concept = ResourceInstance.objects.get(pk=pk)
        except ResourceInstance.DoesNotExist:
            return JSONErrorResponse(
                title=_("Not found"),
                message=_("Concept not found."),
                status=HTTPStatus.NOT_FOUND,
            )

        cascade = request.GET.get("cascade", "").lower() == "true"

        with transaction.atomic():
            unretire_concept(concept, cascade)

        return JSONResponse({"unretired": True})


class SchemeUnretireConceptsView(LingoEditorMixin, View):
    def post(self, request, pk):
        try:
            ResourceInstance.objects.get(pk=pk)
        except ResourceInstance.DoesNotExist:
            return JSONErrorResponse(
                title=_("Not found"),
                message=_("Scheme not found."),
                status=HTTPStatus.NOT_FOUND,
            )

        scheme_id = str(pk)

        concept_ids = set(
            TileModel.objects.filter(
                Q(
                    nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
                    **{
                        f"data__{CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}__contains": [
                            {"resourceId": scheme_id}
                        ]
                    },
                )
                | Q(
                    nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
                    **{
                        f"data__{TOP_CONCEPT_OF_NODE_AND_NODEGROUP}__contains": [
                            {"resourceId": scheme_id}
                        ]
                    },
                )
            )
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

        with transaction.atomic():
            ResourceInstance.objects.filter(
                pk__in=concept_ids,
                resource_instance_lifecycle_state_id=RETIRED_STATE_ID,
            ).update(resource_instance_lifecycle_state_id=EDITING_STATE_ID)

        return JSONResponse({"unretired": True})
