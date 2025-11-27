from http import HTTPStatus

from django.core.paginator import Paginator
from django.db.models import Min, Case, When, Value, IntegerField
from django.db.models.functions import Lower
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models.system_settings import settings
from arches.app.utils.betterJSONSerializer import JSONDeserializer, JSONSerializer
from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_querysets.models import ResourceTileTree, TileTree
from arches_lingo.querysets import fuzzy_search
from arches_lingo.utils.concept_builder import ConceptBuilder


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
        max_edit_distance = self.resolve_max_edit_distance(
            term,
            request.GET.get("maxEditDistance"),
        )
        exact = request.GET.get("exact", False)
        page_number = request.GET.get("page", 1)
        items_per_page = request.GET.get("items", 25)
        order_mode = request.GET.get("order", "unsorted")

        labels = TileTree.get_tiles("concept", nodegroup_alias="appellative_status")

        if exact and term:
            concept_query = labels.filter(appellative_status_ascribed_name_content=term)
            concept_ids = self.build_concept_ids_for_non_fuzzy(
                concept_query,
                order_mode,
            )
        elif term:
            try:
                concept_ids = self.build_ranked_concept_ids_for_term(
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
            concept_ids = self.build_concept_ids_for_non_fuzzy(
                concept_query,
                order_mode,
            )

        paginator = Paginator(concept_ids, items_per_page)
        page = paginator.get_page(page_number)

        data = []
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

    @staticmethod
    def resolve_max_edit_distance(term, raw_max_edit_distance):
        if raw_max_edit_distance is not None:
            base_max_edit_distance = int(raw_max_edit_distance)
        else:
            elastic_prefix_length = settings.SEARCH_TERM_SENSITIVITY

            if elastic_prefix_length <= 0:
                base_max_edit_distance = 5
            elif elastic_prefix_length >= 5:
                base_max_edit_distance = 0
            else:
                base_max_edit_distance = int(5 - elastic_prefix_length)

        if not term:
            return base_max_edit_distance

        term_length = len(term)

        if term_length <= 3:
            return 0

        if term_length <= 5:
            return min(base_max_edit_distance, 1)

        return min(base_max_edit_distance, 2)

    @staticmethod
    def build_ranked_concept_ids_for_term(
        labels,
        term,
        max_edit_distance,
        order_mode,
    ):
        fuzzy_tiles = fuzzy_search(labels, term, max_edit_distance)

        ranked_tiles = fuzzy_tiles.annotate(
            text_rank=Case(
                When(
                    appellative_status_ascribed_name_content__iexact=term,
                    then=Value(0),
                ),
                When(
                    appellative_status_ascribed_name_content__istartswith=term,
                    then=Value(1),
                ),
                When(
                    appellative_status_ascribed_name_content__icontains=term,
                    then=Value(2),
                ),
                default=Value(3),
                output_field=IntegerField(),
            )
        )

        base_query = ranked_tiles.values("resourceinstance").annotate(
            best_text_rank=Min("text_rank"),
            best_label_rank=Min("label_rank"),
            sort_label=Min(Lower("appellative_status_ascribed_name_content")),
        )

        if order_mode == "alphabetical":
            ordered_query = base_query.order_by("sort_label", "resourceinstance")
        elif order_mode == "reverse-alphabetical":
            ordered_query = base_query.order_by("-sort_label", "resourceinstance")
        else:
            ordered_query = base_query.order_by(
                "best_text_rank",
                "best_label_rank",
                "resourceinstance",
            )

        return ordered_query.values_list("resourceinstance", flat=True)

    @staticmethod
    def build_concept_ids_for_non_fuzzy(labels_queryset, order_mode):
        base_query = labels_queryset.values("resourceinstance").annotate(
            best_label_rank=Min("label_rank"),
            sort_label=Min(Lower("appellative_status_ascribed_name_content")),
        )

        if order_mode == "alphabetical":
            ordered_query = base_query.order_by("sort_label", "resourceinstance")
        elif order_mode == "reverse-alphabetical":
            ordered_query = base_query.order_by("-sort_label", "resourceinstance")
        else:
            ordered_query = base_query.order_by(
                "best_label_rank",
                "resourceinstance",
            )

        return ordered_query.values_list("resourceinstance", flat=True)


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class ConceptResourceView(ConceptTreeView):
    def get(self, request):
        scheme = request.GET.get("scheme", None)
        exclude = request.GET.get("exclude", None)
        term = request.GET.get("term", None)
        page_number = request.GET.get("page", 1)
        items_per_page = request.GET.get("items", 25)
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

        data = []
        paginator = Paginator(concept_ids, items_per_page)
        if paginator.count:
            builder = ConceptBuilder()
            data = [
                builder.serialize_concept(
                    str(concept_uuid), parents=True, children=False
                )
                for concept_uuid in paginator.get_page(page_number)
            ]

        return JSONResponse(
            {
                "current_page": paginator.get_page(page_number).number,
                "total_pages": paginator.num_pages,
                "results_per_page": paginator.per_page,
                "total_results": paginator.count,
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
