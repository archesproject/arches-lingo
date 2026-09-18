import json
from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models.models import ResourceInstance
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.mixins.permissions import LingoEditorMixin
from arches_lingo.permissions import is_lingo_admin
from arches_lingo.utils.concept_merge import (
    ConceptMergeError,
    merge_concepts,
    validate_merge,
)


class ConceptMergeView(LingoEditorMixin, View):
    def post(self, request, pk):
        try:
            selections = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JSONErrorResponse(
                title=_("Invalid request"),
                message=_("Request body must be valid JSON."),
                status=HTTPStatus.BAD_REQUEST,
            )

        absorbed_concept_id = selections.get("absorbed_concept_id")
        if not absorbed_concept_id:
            return JSONErrorResponse(
                title=_("Invalid request"),
                message=_("An absorbed_concept_id is required."),
                status=HTTPStatus.BAD_REQUEST,
            )

        try:
            survivor = ResourceInstance.objects.select_related(
                "resource_instance_lifecycle_state"
            ).get(pk=pk)
            absorbed = ResourceInstance.objects.select_related(
                "resource_instance_lifecycle_state"
            ).get(pk=absorbed_concept_id)
        except (ResourceInstance.DoesNotExist, ValueError, ValidationError):
            return JSONErrorResponse(
                title=_("Not found"),
                message=_("Concept not found."),
                status=HTTPStatus.NOT_FOUND,
            )

        try:
            validate_merge(
                survivor,
                absorbed,
                selections.get("tile_selections") or [],
                is_lingo_admin(request.user),
            )
            concept_merge = merge_concepts(survivor, absorbed, selections, request.user)
        except ConceptMergeError as error:
            return JSONErrorResponse(
                title=error.title,
                message=error.message,
                status=error.status,
            )

        return JSONResponse(
            {
                "merged": True,
                "concept_merge_id": concept_merge.pk,
                "edit_transaction_id": str(concept_merge.edit_transaction_id),
            }
        )
