from http import HTTPStatus

from django.conf import settings
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.utils.translation import get_language, gettext as _
from django.views.generic import View

from arches.app.utils.betterJSONSerializer import JSONDeserializer, JSONSerializer
from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_querysets.models import ResourceTileTree, TileTree
from arches_lingo.utils.concept_builder import ConceptBuilder
from arches_lingo.utils.concepts import (
    resolve_max_edit_distance,
    build_ranked_concept_ids_for_term,
    build_concept_ids_for_non_fuzzy,
    rank_concepts_for_unsorted_term,
)


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class ConceptTreeView(View):
    def get(self, request):
        builder = ConceptBuilder()
        data = {
            "schemes": [builder.serialize_scheme(scheme) for scheme in builder.schemes]
        }
        return JSONResponse(data)


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
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


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
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
                if exclude == "true":
                    concept_query = Concept.exclude(part_of_scheme__id=scheme)
                else:
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


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class ConceptRelationshipView(ConceptTreeView):
    def get(self, request):
        concept_id = request.GET.get("concept")
        relationship_type = request.GET.get("type")
        Concept = ResourceTileTree.get_tiles("concept", as_representation=True)

        concept = Concept.get(pk=concept_id)

        if relationship_type == "associated":
            relationships = concept.aliased_data.relation_status
        elif relationship_type == "matched":
            relationships = concept.aliased_data.match_status

        return_data = {
            "scheme_id": concept.aliased_data.part_of_scheme.aliased_data.part_of_scheme[
                "node_value"
            ],
            "data": [],
        }
        for relationship in relationships:
            data = JSONDeserializer().deserialize(
                JSONSerializer().serialize(relationship)
            )
            aliased_data = JSONDeserializer().deserialize(
                JSONSerializer().serialize(relationship.aliased_data)
            )

            if relationship_type == "associated":
                related_concept_resourceid = (
                    relationship.aliased_data.relation_status_ascribed_comparate[
                        "node_value"
                    ][0]["resourceId"]
                )
            elif relationship_type == "matched":
                related_concept_resourceid = (
                    relationship.aliased_data.match_status_ascribed_comparate[
                        "node_value"
                    ][0]["resourceId"]
                )

            related_concept = Concept.get(pk=related_concept_resourceid)

            if related_concept.aliased_data.uri:
                uri = related_concept.aliased_data.uri.aliased_data.uri_content
            else:
                uri = None

            aliased_data["uri"] = uri
            data["aliased_data"] = aliased_data

            return_data["data"].append(data)

        return JSONResponse(return_data)
