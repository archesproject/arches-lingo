from http import HTTPStatus

from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext as _
from django.views import View

from arches.app.utils.response import JSONErrorResponse

from arches_lingo.mixins.permissions import LingoEditorMixin
from arches_lingo.utils.openrefine_round_trip.exceptions import (
    RoundTripRequestError,
)
from arches_lingo.utils.openrefine_round_trip.match_link_import_service import (
    get_match_link_import,
    is_in_progress,
    parse_scheme_id,
    preview_match_link_import,
    serialize_match_link_import,
    start_match_link_import,
)
from arches_lingo.utils.openrefine_round_trip.worksheet_export import (
    build_worksheet,
)


def invalid_request_response(message):
    return JSONErrorResponse(
        title=_("Invalid request."),
        message=message,
        status=HTTPStatus.BAD_REQUEST,
    )


class ReconciliationWorksheetView(LingoEditorMixin, View):
    """Returns a CSV of concepts to reconcile against external authorities."""

    def post(self, request):
        try:
            worksheet = build_worksheet(request.body, request.user)
        except RoundTripRequestError as request_error:
            return invalid_request_response(str(request_error))

        response = HttpResponse(worksheet, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            'attachment; filename="reconciliation-worksheet.csv"'
        )
        return response


class MatchLinkImportPreviewView(LingoEditorMixin, View):
    """Records an uploaded match-link CSV as an import awaiting the editor's
    go-ahead, and reports each link's outcome."""

    def post(self, request):
        try:
            return JsonResponse(
                preview_match_link_import(
                    request.FILES.get("file"),
                    request.user,
                    parse_scheme_id(request.POST.get("scheme_id")),
                )
            )
        except RoundTripRequestError as request_error:
            return invalid_request_response(str(request_error))


class MatchLinkImportApplyView(LingoEditorMixin, View):
    def post(self, request, pk):
        """Starts a previewed import; while it runs, the response is the
        record to poll."""
        try:
            match_link_import = start_match_link_import(pk, request.user)
        except RoundTripRequestError as request_error:
            return invalid_request_response(str(request_error))
        return JsonResponse(
            serialize_match_link_import(match_link_import),
            status=(
                HTTPStatus.ACCEPTED
                if is_in_progress(match_link_import)
                else HTTPStatus.OK
            ),
        )


class MatchLinkImportDetailView(LingoEditorMixin, View):
    def get(self, request, pk):
        match_link_import = get_match_link_import(pk, request.user)
        if match_link_import is None:
            return JSONErrorResponse(
                title=_("Not found."),
                message=_("That import was not found."),
                status=HTTPStatus.NOT_FOUND,
            )
        return JsonResponse(serialize_match_link_import(match_link_import))
