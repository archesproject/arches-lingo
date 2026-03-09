from http import HTTPStatus

from django.conf import settings
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils.translation import get_language, gettext as _
from django.views.generic import View

from arches.app.utils.betterJSONSerializer import JSONDeserializer, JSONSerializer
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_querysets.models import ResourceTileTree, TileTree
from arches_lingo.mixins.anonymous_access import AnonymousAccessMixin
from arches_lingo.permissions import anonymous_access_allowed, is_authenticated_user
from arches_lingo.utils.concept_builder import ConceptBuilder
from arches_lingo.utils.concepts import (
    resolve_max_edit_distance,
    build_ranked_concept_ids_for_term,
    build_concept_ids_for_non_fuzzy,
    rank_concepts_for_unsorted_term,
)
from arches_lingo.utils.dashboard import (
    get_missing_translation_ids,
    paginate_missing_translations,
    parse_scheme_ids,
)


class ConceptTreeView(AnonymousAccessMixin, View):
    def get(self, request):
        builder = ConceptBuilder()
        data = {
            "schemes": [builder.serialize_scheme(scheme) for scheme in builder.schemes]
        }
        return JSONResponse(data)


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

        labels = TileTree.get_tiles("concept", nodegroup_alias="appellative_status")

        if raw_max_edit_distance is None:
            max_edit_distance = resolve_max_edit_distance(term)
        else:
            max_edit_distance = raw_max_edit_distance

        if exact and term:
            concept_query = labels.filter(appellative_status_ascribed_name_content=term)
            concept_ids = build_concept_ids_for_non_fuzzy(
                concept_query,
                order_mode,
            )
        elif term:
            try:
                concept_ids = build_ranked_concept_ids_for_term(
                    labels,
                    term,
                    max_edit_distance,
                    order_mode,
                )
            except ValueError as value_error:
                return JSONErrorResponse(
                    title=_("Unable to perform search."),
                    message=value_error.args[0],
                    status=HTTPStatus.BAD_REQUEST,
                )
        else:
            concept_query = labels
            concept_ids = build_concept_ids_for_non_fuzzy(
                concept_query,
                order_mode,
            )

        data = []

        if term and order_mode == "unsorted":
            active_language = get_language() or settings.LANGUAGE_CODE
            system_language = settings.LANGUAGE_CODE

            ordered_concepts = rank_concepts_for_unsorted_term(
                concept_ids,
                term,
                active_language,
                system_language,
            )

            paginator = Paginator(ordered_concepts, items_per_page)
            page = paginator.get_page(page_number)

            if paginator.count:
                data = list(page.object_list)
        else:
            paginator = Paginator(concept_ids, items_per_page)
            page = paginator.get_page(page_number)

            if paginator.count:
                concept_builder = ConceptBuilder()
                data = [
                    concept_builder.serialize_concept(
                        str(concept_uuid),
                        parents=True,
                        children=False,
                    )
                    for concept_uuid in page
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
