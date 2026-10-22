from http import HTTPStatus

from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.clickjacking import xframe_options_exempt

from arches.app.utils.response import JSONErrorResponse

from arches_lingo.mixins.permissions import ReconciliationAccessMixin
from arches_lingo.utils.reconciliation.candidates import reconcile_queries
from arches_lingo.utils.reconciliation.extension import (
    extend_concepts,
    propose_properties,
)
from arches_lingo.utils.reconciliation.manifest import build_service_manifest
from arches_lingo.utils.reconciliation.preview import build_concept_preview
from arches_lingo.utils.reconciliation.suggest import SUGGEST_SERVICES
from arches_lingo.utils.reconciliation.visibility import (
    resolve_reconcilable_scheme_id,
)


def invalid_request_response(message):
    return JSONErrorResponse(
        title=_("Invalid reconciliation request."),
        message=message,
        status=HTTPStatus.BAD_REQUEST,
    )


class ReconciliationServiceView(ReconciliationAccessMixin, View):
    """W3C reconciliation service endpoint, global or scoped to one scheme.

    Without a ``queries`` parameter it returns the service manifest; version 0.1
    clients send queries by GET, version 0.2 clients by POST.
    """

    def get(self, request, scheme_identifier=None):
        scheme_id = self.resolve_scheme_scope(scheme_identifier)
        if "queries" not in request.GET and "extend" not in request.GET:
            return JsonResponse(build_service_manifest(scheme_id))
        return self.answer(request.GET, scheme_id)

    def post(self, request, scheme_identifier=None):
        scheme_id = self.resolve_scheme_scope(scheme_identifier)
        if "queries" not in request.POST and "extend" not in request.POST:
            return invalid_request_response(
                _("Expected a queries or extend parameter.")
            )
        return self.answer(request.POST, scheme_id)

    @staticmethod
    def answer(parameters, scheme_id):
        try:
            if "extend" in parameters:
                return JsonResponse(extend_concepts(parameters["extend"]))
            return JsonResponse(reconcile_queries(parameters["queries"], scheme_id))
        except ValueError as value_error:
            return invalid_request_response(str(value_error))

    @staticmethod
    def resolve_scheme_scope(scheme_identifier):
        if scheme_identifier is None:
            return None
        scheme_id = resolve_reconcilable_scheme_id(scheme_identifier)
        if scheme_id is None:
            raise Http404()
        return scheme_id


class ReconciliationPropertyProposalView(ReconciliationAccessMixin, View):
    """Lists the properties OpenRefine can add as columns after reconciling."""

    def get(self, request):
        try:
            return JsonResponse(
                propose_properties(request.GET.get("type"), request.GET.get("limit"))
            )
        except ValueError as value_error:
            return invalid_request_response(str(value_error))


class ReconciliationSuggestView(ReconciliationAccessMixin, View):
    """Entity, type and property autocomplete for OpenRefine's suggest widgets."""

    def get(self, request, suggest_kind):
        suggest_service = SUGGEST_SERVICES.get(suggest_kind)
        if suggest_service is None:
            raise Http404()

        suggest_arguments = {
            "prefix": request.GET.get("prefix"),
            "raw_cursor": request.GET.get("cursor"),
        }
        if suggest_kind == "entity":
            suggest_arguments["scheme_id"] = request.GET.get("type")
        try:
            return JsonResponse(suggest_service(**suggest_arguments))
        except ValueError as value_error:
            return invalid_request_response(str(value_error))


@method_decorator(xframe_options_exempt, name="dispatch")
class ReconciliationPreviewView(ReconciliationAccessMixin, View):
    """HTML card OpenRefine shows in a cross-origin iframe beside a candidate."""

    def get(self, request):
        preview_context = build_concept_preview(request.GET.get("id"))
        if preview_context is None:
            raise Http404()
        return render(
            request, "arches_lingo/reconciliation_preview.htm", preview_context
        )
