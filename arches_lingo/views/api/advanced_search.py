import json
from http import HTTPStatus

from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.models import ConceptSet, SavedSearch
from arches_lingo.utils.search_service import (
    add_members_to_concept_set,
    execute_search,
    fetch_search_options,
    remove_members_from_concept_set,
    serialize_concept_set,
    serialize_concept_set_with_members,
    serialize_saved_search,
)


def _parse_json_body(request):
    """Parse JSON from request body, returning (data, error_response)."""
    try:
        return json.loads(request.body), None
    except (json.JSONDecodeError, ValueError):
        return None, JSONErrorResponse(
            title=_("Invalid request."),
            message=_("Request body must be valid JSON."),
            status=HTTPStatus.BAD_REQUEST,
        )


def _get_user_concept_set(user, pk):
    """Look up a ConceptSet owned by user, returning (instance, error_response)."""
    try:
        return ConceptSet.objects.get(pk=pk, user=user), None
    except ConceptSet.DoesNotExist:
        return None, JSONErrorResponse(
            title=_("Not found."),
            message=_("Concept set not found."),
            status=HTTPStatus.NOT_FOUND,
        )


# ── Views ───────────────────────────────────────────────────────


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class AdvancedSearchView(View):

    def post(self, request):
        body, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        try:
            result = execute_search(
                query=body.get("query", {}),
                user=request.user,
                page_number=body.get("page", 1),
                items_per_page=body.get("items", 25),
            )
        except Exception as err:
            return JSONErrorResponse(
                title=_("Search error."),
                message=str(err),
                status=HTTPStatus.BAD_REQUEST,
            )

        return JSONResponse(result)


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class AdvancedSearchOptionsView(View):

    def get(self, request):
        return JSONResponse(fetch_search_options())


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class SavedSearchListView(View):

    def get(self, request):
        searches = SavedSearch.objects.filter(user=request.user)
        return JSONResponse(
            {"data": [serialize_saved_search(search) for search in searches]}
        )

    def post(self, request):
        body, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        name = body.get("name", "").strip()
        if not name:
            return JSONErrorResponse(
                title=_("Invalid request."),
                message=_("Name is required."),
                status=HTTPStatus.BAD_REQUEST,
            )

        saved_search = SavedSearch.objects.create(
            user=request.user,
            name=name,
            query=body.get("query", {}),
        )
        return JSONResponse(
            serialize_saved_search(saved_search),
            status=HTTPStatus.CREATED,
        )


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class SavedSearchDetailView(View):

    def delete(self, request, pk):
        try:
            search = SavedSearch.objects.get(pk=pk, user=request.user)
        except SavedSearch.DoesNotExist:
            return JSONErrorResponse(
                title=_("Not found."),
                message=_("Saved search not found."),
                status=HTTPStatus.NOT_FOUND,
            )
        search.delete()
        return JSONResponse({"deleted": True})

    def patch(self, request, pk):
        try:
            search = SavedSearch.objects.get(pk=pk, user=request.user)
        except SavedSearch.DoesNotExist:
            return JSONErrorResponse(
                title=_("Not found."),
                message=_("Saved search not found."),
                status=HTTPStatus.NOT_FOUND,
            )

        body, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        if "name" in body:
            search.name = body["name"].strip()
        if "query" in body:
            search.query = body["query"]
        search.save()

        return JSONResponse(serialize_saved_search(search))


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class ConceptSetListView(View):

    def get(self, request):
        concept_sets = ConceptSet.objects.filter(user=request.user)
        return JSONResponse(
            {"data": [serialize_concept_set(cs) for cs in concept_sets]}
        )

    def post(self, request):
        body, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        name = body.get("name", "").strip()
        if not name:
            return JSONErrorResponse(
                title=_("Invalid request."),
                message=_("Name is required."),
                status=HTTPStatus.BAD_REQUEST,
            )

        concept_set = ConceptSet.objects.create(
            user=request.user,
            name=name,
            description=body.get("description", ""),
        )
        return JSONResponse(
            serialize_concept_set(concept_set),
            status=HTTPStatus.CREATED,
        )


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class ConceptSetDetailView(View):

    def get(self, request, pk):
        concept_set, error_response = _get_user_concept_set(request.user, pk)
        if error_response:
            return error_response
        return JSONResponse(serialize_concept_set_with_members(concept_set))

    def patch(self, request, pk):
        concept_set, error_response = _get_user_concept_set(request.user, pk)
        if error_response:
            return error_response

        body, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        if "name" in body:
            concept_set.name = body["name"].strip()
        if "description" in body:
            concept_set.description = body["description"]
        concept_set.save()

        return JSONResponse(serialize_concept_set(concept_set))

    def delete(self, request, pk):
        concept_set, error_response = _get_user_concept_set(request.user, pk)
        if error_response:
            return error_response
        concept_set.delete()
        return JSONResponse({"deleted": True})


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class ConceptSetMembersView(View):

    def post(self, request, pk):
        concept_set, error_response = _get_user_concept_set(request.user, pk)
        if error_response:
            return error_response

        body, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        concept_ids = body.get("concept_ids", [])
        if not concept_ids:
            return JSONErrorResponse(
                title=_("Invalid request."),
                message=_("concept_ids is required."),
                status=HTTPStatus.BAD_REQUEST,
            )

        return JSONResponse(add_members_to_concept_set(concept_set, concept_ids))

    def delete(self, request, pk):
        concept_set, error_response = _get_user_concept_set(request.user, pk)
        if error_response:
            return error_response

        body, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        concept_ids = body.get("concept_ids", [])
        return JSONResponse(remove_members_from_concept_set(concept_set, concept_ids))
