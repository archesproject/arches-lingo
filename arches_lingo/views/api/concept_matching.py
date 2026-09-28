"""HTTP layer for match detection. Everything of substance is in the utils."""

import json
from functools import wraps
from http import HTTPStatus

from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.mixins.permissions import LingoEditorMixin
from arches_lingo.permissions import is_lingo_admin
from arches_lingo.utils.concept_matching import ConceptMatchError
from arches_lingo.utils.concept_matching_service import (
    ConceptMatchRequestError,
    delete_run,
    get_run,
    link_candidates_with_exact_match,
    list_runs,
    parse_candidate_ids,
    parse_detection_request,
    reap_stale_runs,
    serialize_scope_sizes,
    start_detection,
    serialize_candidate_page,
    serialize_run,
    set_candidate_status,
    set_status_for_all,
)


def _parse_json_body(request):
    try:
        body = json.loads(request.body or "{}")
    except (json.JSONDecodeError, ValueError):
        body = None
    if not isinstance(body, dict):
        raise ConceptMatchRequestError(
            _("Invalid request."), _("Request body must be a JSON object.")
        )
    return body


def _responds_with_request_errors(handler):
    @wraps(handler)
    def handle(view, request, *args, **kwargs):
        try:
            return handler(view, request, *args, **kwargs)
        except ConceptMatchRequestError as request_error:
            return JSONErrorResponse(
                title=request_error.title,
                message=request_error.message,
                status=request_error.status,
            )
        except ConceptMatchError as detection_error:
            return JSONErrorResponse(
                title=_("Cannot detect matches"),
                message=str(detection_error),
                status=HTTPStatus.BAD_REQUEST,
            )

    return handle


class ConceptMatchScopeSizeView(LingoEditorMixin, View):
    """How much work a scope implies, so the interface can say so up front."""

    def get(self, request):
        return JSONResponse(serialize_scope_sizes())


class ConceptMatchRunListView(LingoEditorMixin, View):
    def get(self, request):
        # Nothing else is in a position to notice a run whose worker died, and
        # this is the request that is about to report those runs as running.
        reap_stale_runs()
        return JSONResponse(
            {"data": list_runs(request.user, is_lingo_admin(request.user))}
        )

    @_responds_with_request_errors
    def post(self, request):
        detection_request = parse_detection_request(_parse_json_body(request))
        run = start_detection(user=request.user, **detection_request)
        return JSONResponse(
            serialize_run(run, request.user, is_lingo_admin(request.user)),
            status=HTTPStatus.CREATED,
        )


class ConceptMatchRunDetailView(LingoEditorMixin, View):
    @_responds_with_request_errors
    def get(self, request, pk):
        # This is what the interface polls while a run works.
        reap_stale_runs(run_ids=[pk])
        return JSONResponse(
            serialize_run(get_run(pk), request.user, is_lingo_admin(request.user))
        )

    @_responds_with_request_errors
    def delete(self, request, pk):
        delete_run(get_run(pk), request.user, is_lingo_admin(request.user))
        return JSONResponse({"deleted": True})


class ConceptMatchCandidateListView(LingoEditorMixin, View):
    @_responds_with_request_errors
    def get(self, request, pk):
        return JSONResponse(
            serialize_candidate_page(
                get_run(pk),
                status=request.GET.get("status") or None,
                page_number=request.GET.get("page"),
                items_per_page=request.GET.get("items"),
                user_is_lingo_admin=is_lingo_admin(request.user),
            )
        )

    @_responds_with_request_errors
    def patch(self, request, pk):
        """Record a review decision against one or more of the run's candidates."""
        run = get_run(pk)
        body = _parse_json_body(request)

        # Clearing or restoring a whole queue names no ids: there can be tens
        # of thousands of them.
        if body.get("all"):
            return JSONResponse(
                set_status_for_all(run, body.get("status"), request.user)
            )

        return JSONResponse(
            set_candidate_status(
                run, parse_candidate_ids(body), body.get("status"), request.user
            )
        )


class ConceptMatchLinkView(LingoEditorMixin, View):
    """Record an exactMatch between the concepts of each selected candidate."""

    @_responds_with_request_errors
    def post(self, request, pk):
        run = get_run(pk)
        return JSONResponse(
            link_candidates_with_exact_match(
                run,
                parse_candidate_ids(_parse_json_body(request)),
                request.user,
                user_is_lingo_admin=is_lingo_admin(request.user),
            )
        )
