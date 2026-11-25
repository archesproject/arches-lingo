import json
from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models.models import ResourceInstance
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.mixins.permissions import AnonymousAccessMixin, LingoEditorMixin
from arches_lingo.permissions import is_lingo_admin
from arches_lingo.utils.concept_merge.history import get_concept_merge_history
from arches_lingo.utils.concept_merge.preview import build_merge_preview
from arches_lingo.utils.concept_merge.service import merge_concepts
from arches_lingo.utils.concept_merge.validation import (
    ConceptMergeError,
    concept_is_writable,
    validate_merge,
)


def load_concepts(*concept_ids):
    return [
        ResourceInstance.objects.select_related(
            "resource_instance_lifecycle_state"
        ).get(pk=concept_id)
        for concept_id in concept_ids
    ]


def concept_not_found_response():
    return JSONErrorResponse(
        title=_("Not found"),
        message=_("Concept not found."),
        status=HTTPStatus.NOT_FOUND,
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
            survivor, absorbed = load_concepts(pk, absorbed_concept_id)
        except (ResourceInstance.DoesNotExist, ValueError, ValidationError):
            return concept_not_found_response()

        user_is_lingo_admin = is_lingo_admin(request.user)
        try:
            validate_merge(survivor, absorbed, selections, user_is_lingo_admin)
            absorbed_was_writable = concept_is_writable(absorbed, user_is_lingo_admin)
            concept_merge = merge_concepts(
                survivor,
                absorbed,
                selections,
                request.user,
                user_is_lingo_admin=user_is_lingo_admin,
            )
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
                "exact_match_recorded_on_absorbed": absorbed_was_writable,
            }
        )


class ConceptMergePreviewView(LingoEditorMixin, View):
    def get(self, request, pk, absorbed_pk):
        try:
            survivor, absorbed = load_concepts(pk, absorbed_pk)
        except ResourceInstance.DoesNotExist:
            return concept_not_found_response()

        return JSONResponse(build_merge_preview(survivor, absorbed))


class ConceptMergeHistoryView(AnonymousAccessMixin, View):
    def get(self, request, pk):
        return JSONResponse({"merges": get_concept_merge_history(pk)})
