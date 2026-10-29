import json
from datetime import date
from http import HTTPStatus

from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext as _
from django.views import View

from arches.app.utils.response import JSONErrorResponse

from arches_lingo.mixins.permissions import LingoEditorMixin
from arches_lingo.utils.openrefine_round_trip.match_link_import import (
    preview_match_link_import,
)
from arches_lingo.utils.openrefine_round_trip.match_link_import_service import (
    get_match_link_import,
    is_in_progress,
    parse_scheme_id,
    serialize_match_link_import,
    start_match_link_import,
)
from arches_lingo.utils.openrefine_round_trip.worksheet_export import (
    parse_worksheet_scope,
    resolve_worksheet_concept_ids,
    resolve_worksheet_language,
    write_worksheet,
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
            request_body = json.loads(request.body)
            scope_key, scope_value = parse_worksheet_scope(request_body)
            concept_ids = resolve_worksheet_concept_ids(
                scope_key, scope_value, request.user
            )
        except ValueError as value_error:
            return invalid_request_response(str(value_error))

        language = resolve_worksheet_language(request_body.get("language"))
        response = HttpResponse(
            write_worksheet(concept_ids, request.user, language),
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
                preview_match_link_import(
                    request.FILES.get("file"),
                    request.user,
                    parse_scheme_id(request.POST.get("scheme_id")),
                )
            )
        except ValueError as value_error:
            return invalid_request_response(str(value_error))


class MatchLinkImportCreateView(LingoEditorMixin, View):
    def post(self, request):
        """Starts an import; while it runs, the response is the record to poll."""
        try:
            match_link_import = start_match_link_import(
                request.FILES.get("file"),
                request.user,
                parse_scheme_id(request.POST.get("scheme_id")),
            )
        except ValueError as value_error:
            return invalid_request_response(str(value_error))
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
