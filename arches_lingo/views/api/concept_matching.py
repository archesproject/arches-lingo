"""HTTP layer for match detection. Everything of substance is in the utils."""

import json
from http import HTTPStatus

from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.mixins.permissions import LingoEditorMixin
from arches_lingo.permissions import is_lingo_admin
from arches_lingo.models import ConceptMatchRun
from arches_lingo.utils.concept_matching import (
    EXACT_SIGNALS,
    ConceptMatchError,
    MatchScope,
    run_detection,
)
from arches_lingo.utils.concept_matching_service import (
    ConceptMatchRequestError,
    link_candidates_with_exact_match,
    serialize_candidate_page,
    serialize_run,
    set_candidate_status,
)


def _parse_json_body(request):
    try:
        return json.loads(request.body or "{}"), None
    except (json.JSONDecodeError, ValueError):
        return None, JSONErrorResponse(
            title=_("Invalid request."),
            message=_("Request body must be valid JSON."),
            status=HTTPStatus.BAD_REQUEST,
        )


def _get_user_run(user, pk):
    try:
        return ConceptMatchRun.objects.get(pk=pk, user=user), None
    except ConceptMatchRun.DoesNotExist:
        return None, JSONErrorResponse(
            title=_("Not found."),
            message=_("Match run not found."),
            status=HTTPStatus.NOT_FOUND,
        )


class ConceptMatchRunListView(LingoEditorMixin, View):
    def get(self, request):
        runs = ConceptMatchRun.objects.filter(user=request.user)
        return JSONResponse({"data": [serialize_run(run) for run in runs]})

    def post(self, request):
        body, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        scope = MatchScope(
            source_scheme_id=body.get("source_scheme_id") or None,
            target_scheme_id=body.get("target_scheme_id") or None,
            source_concept_set_id=body.get("source_concept_set_id") or None,
            source_concept_ids=body.get("source_concept_ids") or [],
            cross_scheme_only=bool(body.get("cross_scheme_only")),
        )

        try:
            run = run_detection(
                scope,
                signals=tuple(body.get("signals") or EXACT_SIGNALS),
                same_language_only=body.get("same_language_only", True),
                user=request.user,
                log=lambda message: None,
            )
        except ConceptMatchError as detection_error:
            return JSONErrorResponse(
                title=_("Cannot detect matches"),
                message=str(detection_error),
                status=HTTPStatus.BAD_REQUEST,
            )

        return JSONResponse(serialize_run(run), status=HTTPStatus.CREATED)


class ConceptMatchRunDetailView(LingoEditorMixin, View):
    def get(self, request, pk):
        run, error_response = _get_user_run(request.user, pk)
        if error_response:
            return error_response
        return JSONResponse(serialize_run(run))

    def delete(self, request, pk):
        run, error_response = _get_user_run(request.user, pk)
        if error_response:
            return error_response
        run.delete()
        return JSONResponse({"deleted": True})


class ConceptMatchCandidateListView(LingoEditorMixin, View):
    def get(self, request, pk):
        run, error_response = _get_user_run(request.user, pk)
        if error_response:
            return error_response

        return JSONResponse(
            serialize_candidate_page(
                run,
                status=request.GET.get("status") or None,
                page_number=request.GET.get("page", 1),
                items_per_page=request.GET.get("items"),
            )
        )

    def patch(self, request, pk):
        """Record a review decision against one or more of the run's candidates."""
        run, error_response = _get_user_run(request.user, pk)
        if error_response:
            return error_response

        body, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        candidate_ids = body.get("candidate_ids") or []
        if not candidate_ids:
            return JSONErrorResponse(
                title=_("Invalid request."),
                message=_("candidate_ids is required."),
                status=HTTPStatus.BAD_REQUEST,
            )

        try:
            result = set_candidate_status(
                run, candidate_ids, body.get("status"), request.user
            )
        except ConceptMatchRequestError as request_error:
            return JSONErrorResponse(
                title=request_error.title,
                message=request_error.message,
                status=request_error.status,
            )

        return JSONResponse(result)


class ConceptMatchLinkView(LingoEditorMixin, View):
    """Record an exactMatch between the concepts of each selected candidate."""

    def post(self, request, pk):
        run, error_response = _get_user_run(request.user, pk)
        if error_response:
            return error_response

        body, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        candidate_ids = body.get("candidate_ids") or []
        if not candidate_ids:
            return JSONErrorResponse(
                title=_("Invalid request."),
                message=_("candidate_ids is required."),
                status=HTTPStatus.BAD_REQUEST,
            )

        try:
            result = link_candidates_with_exact_match(
                run,
                candidate_ids,
                request.user,
                user_is_lingo_admin=is_lingo_admin(request.user),
            )
        except ConceptMatchRequestError as request_error:
            return JSONErrorResponse(
                title=request_error.title,
                message=request_error.message,
                status=request_error.status,
            )

        return JSONResponse(result)
