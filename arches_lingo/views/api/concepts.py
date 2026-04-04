from http import HTTPStatus

from django.conf import settings
from django.core.paginator import Paginator
from django.db import transaction
from django.utils.translation import get_language, gettext as _
from django.views.generic import View

from arches.app.models.models import ResourceInstance
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_querysets.models import ResourceTileTree
from arches_lingo.mixins.permissions import AnonymousAccessMixin, LingoEditorMixin
from arches_lingo.utils.concept_builder import ConceptBuilder
from arches_lingo.utils.concept_lifecycle import (
    DRAFT_STATE_ID,
    VALID_STRATEGIES,
    delete_concept,
    get_narrower_ids,
)
from arches_lingo.utils.concepts import (
    resolve_max_edit_distance,
    build_search_queryset,
    build_concept_ids_for_non_fuzzy,
    SearchResultSet,
)
from arches_lingo.utils.dashboard import (
    get_missing_translation_ids,
    paginate_missing_translations,
    parse_scheme_ids,
)


class ConceptTreeView(AnonymousAccessMixin, View):
    def get(self, request):
        builder = ConceptBuilder(shallow=True)
        data = {
            "schemes": [
                builder.serialize_scheme(scheme, shallow=True)
                for scheme in builder.schemes
            ]
        }
        return JSONResponse(data)


class ConceptChildrenView(AnonymousAccessMixin, View):
    def get(self, request, concept_id):
        builder = ConceptBuilder.for_concept_children(str(concept_id))
        children = [
            builder.serialize_concept_shallow(child_id)
            for child_id in sorted(
                builder.narrower_concepts.get(str(concept_id), set())
            )
        ]
        return JSONResponse({"children": children})


class ConceptAncestorsView(AnonymousAccessMixin, View):
    def get(self, request, concept_id):
        concept_id_str = str(concept_id)
        builder = ConceptBuilder([concept_id_str], include_parents=True)
        paths = builder.find_paths_to_root([concept_id_str], concept_id_str)

        ancestor_paths = []
        for path in paths:
            search_results = []
            for node_id in path:
                scheme = builder.lookup_scheme(node_id)
                if scheme is not None:
                    search_results.append(
                        builder.serialize_scheme(scheme, children=False)
                    )
                else:
                    search_results.append(
                        builder.serialize_concept(
                            node_id, parents=False, children=False
                        )
                    )
            ancestor_paths.append({"searchResults": search_results})

        return JSONResponse({"paths": ancestor_paths})


class ValueSearchView(ConceptTreeView):
    def get(self, request):
        term = request.GET.get("term")
        raw_max_edit_distance = request.GET.get("maxEditDistance")
        exact = request.GET.get("exact", False)
        page_number = request.GET.get("page", 1)
        items_per_page = request.GET.get("items", 25)

        order_mode = request.GET.get("order", "unsorted")
        if order_mode not in ("alphabetical", "reverse-alphabetical", "unsorted"):
            order_mode = "unsorted"

        if raw_max_edit_distance is None:
            max_edit_distance = resolve_max_edit_distance(term)
        else:
            max_edit_distance = raw_max_edit_distance

        if exact and term:
            concept_ids = SearchResultSet(
                term=term,
                use_fuzzy=False,
                similarity_threshold=1.0,
                order_mode=order_mode,
                active_language="",
                system_language="",
                exact_match=True,
            )
        elif term:
            active_language = get_language() or settings.LANGUAGE_CODE
            system_language = settings.LANGUAGE_CODE
            try:
                concept_ids = build_search_queryset(
                    None,
                    term,
                    max_edit_distance,
                    order_mode,
                    active_language,
                    system_language,
                )
            except ValueError as value_error:
                return JSONErrorResponse(
                    title=_("Unable to perform search."),
                    message=value_error.args[0],
                    status=HTTPStatus.BAD_REQUEST,
                )
        else:
            concept_ids = build_concept_ids_for_non_fuzzy(None, order_mode)

        paginator = Paginator(concept_ids, items_per_page)
        page = paginator.get_page(page_number)

        data = []
        if paginator.count:
            page_concept_ids = [str(concept_uuid) for concept_uuid in page]
            concept_builder = ConceptBuilder(page_concept_ids, include_parents=True)
            data = [
                concept_builder.serialize_concept(
                    concept_id,
                    parents=True,
                    children=False,
                )
                for concept_id in page_concept_ids
            ]

        return JSONResponse(
            {
                "current_page": page.number,
                "total_pages": paginator.num_pages,
                "results_per_page": paginator.per_page,
                "total_results": paginator.count,
                "data": data,
            }
        )


class ConceptResourceView(ConceptTreeView):
    def get(self, request):
        scheme = request.GET.get("scheme", None)
        exclude = request.GET.get("exclude", None)
        excluded_ids = exclude.split(",") if exclude else None
        term = request.GET.get("term", None)
        page_number = int(request.GET.get("page", 1))
        items_per_page = int(request.GET.get("items", 25))
        concepts = request.GET.get("concepts", None)
        concept_ids = concepts.split(",") if concepts else None
        Concept = ResourceTileTree.get_tiles("concept")

        if not concept_ids:
            if scheme:
                concept_query = Concept.filter(part_of_scheme__id=scheme)
            else:
                concept_query = Concept.all()

            if term:
                concept_query = concept_query.filter(
                    appellative_status_ascribed_name_content__icontains=term
                )
            if exclude:
                concept_query = concept_query.exclude(pk__in=excluded_ids)

            concept_ids = concept_query.order_by("pk").values_list("pk", flat=True)

        paginator = Paginator(concept_ids, items_per_page)
        page = paginator.get_page(page_number)
        total_results = paginator.count

        data = []
        if total_results:
            page_concept_ids = [str(concept_uuid) for concept_uuid in page]
            builder = ConceptBuilder(page_concept_ids, include_parents=True)
            data = [
                builder.serialize_concept(concept_id, parents=True, children=False)
                for concept_id in page_concept_ids
            ]

        return JSONResponse(
            {
                "current_page": page.number,
                "total_pages": paginator.num_pages,
                "results_per_page": paginator.per_page,
                "total_results": total_results,
                "data": data,
            }
        )


class ConceptRelationshipView(ConceptTreeView):
    def get(self, request):
        concept_id = request.GET.get("concept")
        Concept = ResourceTileTree.get_tiles("concept", as_representation=True)
        concept = Concept.get(pk=concept_id)
        relationships = concept.aliased_data.relation_status

        return_data = {
            "scheme_id": concept.aliased_data.part_of_scheme.aliased_data.part_of_scheme[
                "node_value"
            ][
                0
            ][
                "resourceId"
            ],
            "data": relationships,
        }

        return JSONResponse(return_data)


class ConceptDeleteView(LingoEditorMixin, View):
    def delete(self, request, pk):
        try:
            concept = ResourceInstance.objects.get(pk=pk)
        except ResourceInstance.DoesNotExist:
            return JSONErrorResponse(
                title=_("Not found"),
                message=_("Concept not found."),
                status=HTTPStatus.NOT_FOUND,
            )

        if concept.resource_instance_lifecycle_state_id != DRAFT_STATE_ID:
            return JSONErrorResponse(
                title=_("Cannot delete"),
                message=_("Only concepts in Draft state can be deleted."),
                status=HTTPStatus.BAD_REQUEST,
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

        try:
            with transaction.atomic():
                delete_concept(concept, strategy)
        except ValueError as error:
            return JSONErrorResponse(
                title=_("Cannot delete"),
                message=str(error),
                status=HTTPStatus.BAD_REQUEST,
            )

        return JSONResponse({"deleted": True})


class ConceptMissingTranslationsView(AnonymousAccessMixin, View):
    def get(self, request):
        language_code = request.GET.get("language")
        if not language_code:
            return JSONErrorResponse(
                title=_("Missing parameter"),
                message=_("language parameter is required"),
                status=400,
            )

        try:
            scheme_ids = parse_scheme_ids(request)
        except ValueError as error:
            return JSONErrorResponse(
                title=_("Invalid scheme"),
                message=str(error),
                status=400,
            )

        page_number = int(request.GET.get("page", 1))
        items_per_page = int(request.GET.get("items", 25))

        missing_ids = get_missing_translation_ids(language_code, scheme_ids)

        return JSONResponse(
            paginate_missing_translations(missing_ids, page_number, items_per_page)
        )
