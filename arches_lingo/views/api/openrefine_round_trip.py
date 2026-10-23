import json
from datetime import date
from http import HTTPStatus

from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.views import View

from arches.app.utils.response import JSONErrorResponse

from arches_lingo.mixins.permissions import LingoEditorMixin
from arches_lingo.models import MatchLinkImport
from arches_lingo.permissions import is_lingo_admin
from arches_lingo.utils.openrefine_round_trip.match_link_import import (
    preview_match_link_import,
    serialize_match_link_import,
    start_match_link_import,
)
from arches_lingo.utils.openrefine_round_trip.worksheet_export import (
    parse_worksheet_scope,
    resolve_worksheet_concept_ids,
    stream_worksheet,
)


def invalid_request_response(message):
    return JSONErrorResponse(
        title=_("Invalid request."),
        message=message,
        status=HTTPStatus.BAD_REQUEST,
    )


class ReconciliationWorksheetView(LingoEditorMixin, View):
    """Streams a CSV of concepts to reconcile against external authorities."""

    def post(self, request):
        try:
            request_body = json.loads(request.body)
            scope_key, scope_value = parse_worksheet_scope(request_body)
            concept_ids = resolve_worksheet_concept_ids(
                scope_key, scope_value, request.user
            )
        except ValueError as value_error:
            return invalid_request_response(str(value_error))

        language = (
            request_body.get("language") or get_language() or settings.LANGUAGE_CODE
        )
        response = StreamingHttpResponse(
            stream_worksheet(concept_ids, request.user, language),
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="reconciliation-worksheet-{date.today()}.csv"'
        )
        return response


class MatchLinkImportPreviewView(LingoEditorMixin, View):
    """Validates an uploaded match-link CSV and reports each row's outcome."""

    def post(self, request):
        try:
            return JsonResponse(
                preview_match_link_import(request.FILES.get("file"), request.user)
            )
        except ValueError as value_error:
            return invalid_request_response(str(value_error))


class MatchLinkImportListView(LingoEditorMixin, View):
    """Starts an import; the response is the record to poll."""

    def post(self, request):
        try:
            match_link_import = start_match_link_import(
                request.FILES.get("file"), request.user
            )
        except ValueError as value_error:
            return invalid_request_response(str(value_error))
        return JsonResponse(
            serialize_match_link_import(match_link_import),
            status=HTTPStatus.ACCEPTED,
        )


class MatchLinkImportDetailView(LingoEditorMixin, View):
    def get(self, request, pk):
        match_link_import = MatchLinkImport.objects.filter(pk=pk).first()
        if match_link_import is None or (
            match_link_import.user_id != request.user.pk
            and not is_lingo_admin(request.user)
        ):
            return JSONErrorResponse(
                title=_("Not found."),
                message=_("That import was not found."),
                status=HTTPStatus.NOT_FOUND,
            )
        return JsonResponse(serialize_match_link_import(match_link_import))
