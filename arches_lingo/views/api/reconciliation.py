from http import HTTPStatus

from django.http import Http404, JsonResponse
from django.utils.translation import gettext as _
from django.views import View

from arches.app.utils.response import JSONErrorResponse

from arches_lingo.mixins.permissions import ReconciliationAccessMixin
from arches_lingo.utils.reconciliation.candidates import reconcile_queries
from arches_lingo.utils.reconciliation.manifest import build_service_manifest
from arches_lingo.utils.reconciliation.visibility import (
    resolve_reconcilable_scheme_id,
)


class ReconciliationServiceView(ReconciliationAccessMixin, View):
    """W3C reconciliation service endpoint, global or scoped to one scheme.

    Without a ``queries`` parameter it returns the service manifest; version 0.1
    clients send queries by GET, version 0.2 clients by POST.
    """

    def get(self, request, scheme_identifier=None):
        scheme_id = self.resolve_scheme_scope(scheme_identifier)
        raw_queries = request.GET.get("queries")
        if raw_queries is None:
            return JsonResponse(build_service_manifest(scheme_id))
        return self.reconcile(raw_queries, scheme_id)

    def post(self, request, scheme_identifier=None):
        scheme_id = self.resolve_scheme_scope(scheme_identifier)
        raw_queries = request.POST.get("queries")
        if raw_queries is None:
            return JSONErrorResponse(
                title=_("Invalid reconciliation request."),
                message=_("Expected a queries parameter."),
                status=HTTPStatus.BAD_REQUEST,
            )
        return self.reconcile(raw_queries, scheme_id)

    @staticmethod
    def resolve_scheme_scope(scheme_identifier):
        if scheme_identifier is None:
            return None
        scheme_id = resolve_reconcilable_scheme_id(scheme_identifier)
        if scheme_id is None:
            raise Http404()
        return scheme_id

    @staticmethod
    def reconcile(raw_queries, scheme_id):
        try:
            return JsonResponse(reconcile_queries(raw_queries, scheme_id))
        except ValueError as value_error:
            return JSONErrorResponse(
                title=_("Invalid reconciliation request."),
                message=str(value_error),
                status=HTTPStatus.BAD_REQUEST,
            )
