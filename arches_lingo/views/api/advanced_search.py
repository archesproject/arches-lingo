import json
from http import HTTPStatus

from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models.models import Language, ResourceInstance, TileModel
from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.const import CONCEPTS_GRAPH_ID
from arches_lingo.models import ConceptSet, ConceptSetMember, SavedSearch
from arches_lingo.const import (
    IDENTIFIER_CONTENT_NODE,
    IDENTIFIER_NODEGROUP,
    STATEMENT_CONTENT_NODE,
    STATEMENT_LANGUAGE_NODE,
    STATEMENT_NODEGROUP,
    STATEMENT_TYPE_NODE,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)
from arches_lingo.utils.advanced_search import AdvancedSearchEvaluator
from arches_lingo.utils.concept_builder import ConceptBuilder


# ── Helpers ─────────────────────────────────────────────────────


def _parse_json_body(request):
    """Parse JSON from request body.

    Returns (data, None) on success or (None, error_response) on failure.
    """
    try:
        return json.loads(request.body), None
    except (json.JSONDecodeError, ValueError):
        return None, JSONErrorResponse(
            title=_("Invalid request."),
            message=_("Request body must be valid JSON."),
            status=HTTPStatus.BAD_REQUEST,
        )


def _serialize_saved_search(saved_search):
    """Serialize a SavedSearch instance to a dict."""
    return {
        "id": saved_search.pk,
        "name": saved_search.name,
        "query": saved_search.query,
        "created": saved_search.created.isoformat(),
        "updated": saved_search.updated.isoformat(),
    }


def _serialize_concept_set(concept_set):
    """Serialize a ConceptSet instance to a dict with member count."""
    return {
        "id": concept_set.pk,
        "name": concept_set.name,
        "description": concept_set.description,
        "member_count": concept_set.members.count(),
        "created": concept_set.created.isoformat(),
        "updated": concept_set.updated.isoformat(),
    }


def _get_user_concept_set(request, pk):
    """Look up a ConceptSet owned by request.user.

    Returns (instance, None) or (None, error_response).
    """
    try:
        return ConceptSet.objects.get(pk=pk, user=request.user), None
    except ConceptSet.DoesNotExist:
        return None, JSONErrorResponse(
            title=_("Not found."),
            message=_("Concept set not found."),
            status=HTTPStatus.NOT_FOUND,
        )


def _extract_note_type_label(note_type_data):
    """Extract a human-readable label from reference-data note type JSON.

    Prefers English; falls back to the first available label.
    """
    if not note_type_data or not isinstance(note_type_data, list):
        return ""
    labels = note_type_data[0].get("labels", [])
    for label in labels:
        if label.get("language_id") == "en":
            return label.get("value", "")
    if labels:
        return labels[0].get("value", "")
    return ""


# ── Views ───────────────────────────────────────────────────────


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class AdvancedSearchView(View):
    """Execute an advanced search query and return paginated results."""

    def post(self, request):
        body, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        query = body.get("query", {})
        page_number = body.get("page", 1)
        items_per_page = body.get("items", 25)

        try:
            evaluator = AdvancedSearchEvaluator(user=request.user)
            concept_ids = evaluator.evaluate(query)
        except Exception as err:
            return JSONErrorResponse(
                title=_("Search error."),
                message=str(err),
                status=HTTPStatus.BAD_REQUEST,
            )

        paginator = Paginator(concept_ids, items_per_page)
        page = paginator.get_page(page_number)

        data = []
        if paginator.count:
            page_ids = [str(concept_id) for concept_id in page]
            builder = ConceptBuilder(page_ids, include_parents=True)
            data = [self._enrich_result(builder, concept_id) for concept_id in page_ids]

        return JSONResponse(
            {
                "current_page": page.number,
                "total_pages": paginator.num_pages,
                "results_per_page": paginator.per_page,
                "total_results": paginator.count,
                "data": data,
            }
        )

    def _enrich_result(self, builder, concept_id):
        """Serialize a concept with extra fields for advanced search results."""
        result = builder.serialize_concept(concept_id, parents=True, children=False)
        result["uri"] = self._get_first_uri(concept_id)
        result["identifier"] = self._get_first_identifier(concept_id)
        result["notes"] = self._get_notes(concept_id)
        result["lifecycle_state"] = self._get_lifecycle_state(concept_id)
        return result

    @staticmethod
    def _get_first_uri(concept_id):
        """Extract the first URI value from URI tiles."""
        tile = TileModel.objects.filter(
            resourceinstance_id=concept_id,
            nodegroup_id=URI_NODEGROUP,
        ).first()
        if not tile:
            return None
        uri_data = tile.data.get(URI_CONTENT_NODE)
        if isinstance(uri_data, dict):
            return uri_data.get("url")
        if isinstance(uri_data, str):
            return uri_data
        return None

    @staticmethod
    def _get_first_identifier(concept_id):
        """Extract the first identifier value from identifier tiles."""
        tile = TileModel.objects.filter(
            resourceinstance_id=concept_id,
            nodegroup_id=IDENTIFIER_NODEGROUP,
        ).first()
        if not tile:
            return None
        return tile.data.get(IDENTIFIER_CONTENT_NODE)

    @staticmethod
    def _get_notes(concept_id, limit=3):
        """Extract note summaries from statement tiles."""
        note_tiles = TileModel.objects.filter(
            resourceinstance_id=concept_id,
            nodegroup_id=STATEMENT_NODEGROUP,
        )[:limit]

        notes = []
        for tile in note_tiles:
            content = tile.data.get(STATEMENT_CONTENT_NODE, "")
            language = tile.data.get(STATEMENT_LANGUAGE_NODE, "")
            note_type = _extract_note_type_label(tile.data.get(STATEMENT_TYPE_NODE, []))
            notes.append(
                {
                    "content": content or "",
                    "language": language or "",
                    "type": note_type,
                }
            )
        return notes

    @staticmethod
    def _get_lifecycle_state(concept_id):
        """Get the lifecycle state name for a concept."""
        try:
            resource = ResourceInstance.objects.get(pk=concept_id)
            state = resource.resource_instance_lifecycle_state
            return state.name if state else None
        except ResourceInstance.DoesNotExist:
            return None


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class AdvancedSearchOptionsView(View):
    """Return filter option data for the advanced search UI."""

    def get(self, request):
        """Return available languages, schemes, and lifecycle states."""
        languages = list(
            Language.objects.filter(isdefault=True)
            .union(Language.objects.filter(scope="system"))
            .values("code", "name")
            .order_by("name")
        )
        # Fallback: just get all languages
        if not languages:
            languages = list(
                Language.objects.all().values("code", "name").order_by("name")
            )

        scheme_builder = ConceptBuilder()
        scheme_options = []
        for scheme in scheme_builder.schemes:
            serialized = scheme_builder.serialize_scheme(scheme, children=False)
            label = self._extract_pref_label(serialized)
            scheme_options.append(
                {
                    "id": serialized["id"],
                    "label": label,
                }
            )

        # Lifecycle states
        from arches.app.models.models import ResourceInstanceLifecycleState

        lifecycle_states = list(
            ResourceInstanceLifecycleState.objects.filter(
                resource_instance_lifecycle__graphs__graphid=CONCEPTS_GRAPH_ID
            )
            .values("id", "name")
            .distinct()
            .order_by("name")
        )

        return JSONResponse(
            {
                "languages": languages,
                "schemes": scheme_options,
                "lifecycle_states": lifecycle_states,
            }
        )

    @staticmethod
    def _extract_pref_label(serialized_scheme):
        """Extract the preferred label from a serialized scheme."""
        for label in serialized_scheme.get("labels", []):
            if label.get("valuetype_id") == "prefLabel":
                return label.get("value", "")
        labels = serialized_scheme.get("labels", [])
        if labels:
            return labels[0].get("value", "")
        return ""


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class SavedSearchListView(View):
    """List and create saved searches."""

    def get(self, request):
        searches = SavedSearch.objects.filter(user=request.user)
        data = [_serialize_saved_search(search) for search in searches]
        return JSONResponse({"data": data})

    def post(self, request):
        body, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        name = body.get("name", "").strip()
        query = body.get("query", {})

        if not name:
            return JSONErrorResponse(
                title=_("Invalid request."),
                message=_("Name is required."),
                status=HTTPStatus.BAD_REQUEST,
            )

        saved_search = SavedSearch.objects.create(
            user=request.user,
            name=name,
            query=query,
        )
        return JSONResponse(
            _serialize_saved_search(saved_search),
            status=HTTPStatus.CREATED,
        )


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class SavedSearchDetailView(View):
    """Update and delete saved searches."""

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

        return JSONResponse(_serialize_saved_search(search))


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class ConceptSetListView(View):
    """List and create concept sets."""

    def get(self, request):
        concept_sets = ConceptSet.objects.filter(user=request.user)
        data = [_serialize_concept_set(concept_set) for concept_set in concept_sets]
        return JSONResponse({"data": data})

    def post(self, request):
        body, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        name = body.get("name", "").strip()
        description = body.get("description", "")

        if not name:
            return JSONErrorResponse(
                title=_("Invalid request."),
                message=_("Name is required."),
                status=HTTPStatus.BAD_REQUEST,
            )

        concept_set = ConceptSet.objects.create(
            user=request.user,
            name=name,
            description=description,
        )
        return JSONResponse(
            _serialize_concept_set(concept_set),
            status=HTTPStatus.CREATED,
        )


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class ConceptSetDetailView(View):
    """Update, delete, and manage concept sets."""

    def get(self, request, pk):
        """Get a concept set with its members."""
        concept_set, error_response = _get_user_concept_set(request, pk)
        if error_response:
            return error_response

        member_ids = list(concept_set.members.values_list("concept_id", flat=True))

        # Serialize members
        data = []
        if member_ids:
            str_ids = [str(member_id) for member_id in member_ids]
            builder = ConceptBuilder(str_ids, include_parents=True)
            data = [
                builder.serialize_concept(concept_id, parents=True, children=False)
                for concept_id in str_ids
            ]

        return JSONResponse(
            {
                "id": concept_set.pk,
                "name": concept_set.name,
                "description": concept_set.description,
                "members": data,
                "created": concept_set.created.isoformat(),
                "updated": concept_set.updated.isoformat(),
            }
        )

    def patch(self, request, pk):
        concept_set, error_response = _get_user_concept_set(request, pk)
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

        return JSONResponse(_serialize_concept_set(concept_set))

    def delete(self, request, pk):
        concept_set, error_response = _get_user_concept_set(request, pk)
        if error_response:
            return error_response

        concept_set.delete()
        return JSONResponse({"deleted": True})


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class ConceptSetMembersView(View):
    """Add/remove members from a concept set."""

    def post(self, request, pk):
        """Add concepts to a set."""
        concept_set, error_response = _get_user_concept_set(request, pk)
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

        added = 0
        for concept_id in concept_ids:
            _member, created = ConceptSetMember.objects.get_or_create(
                concept_set=concept_set,
                concept_id=concept_id,
            )
            if created:
                added += 1

        return JSONResponse(
            {
                "added": added,
                "member_count": concept_set.members.count(),
            }
        )

    def delete(self, request, pk):
        """Remove concepts from a set."""
        concept_set, error_response = _get_user_concept_set(request, pk)
        if error_response:
            return error_response

        body, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        concept_ids = body.get("concept_ids", [])
        if concept_ids:
            concept_set.members.filter(concept_id__in=concept_ids).delete()

        return JSONResponse(
            {
                "member_count": concept_set.members.count(),
            }
        )
