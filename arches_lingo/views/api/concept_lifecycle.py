from http import HTTPStatus

from django.db import transaction
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models.models import ResourceInstance
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.mixins.permissions import LingoEditorMixin
from arches_lingo.utils.concept_lifecycle import (
    VALID_STRATEGIES,
    get_narrower_ids,
    retire_concept,
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
