from http import HTTPStatus

from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.utils.translation import get_language, gettext as _
from django.views.generic import View

from arches.app.models.system_settings import settings
from arches.app.models.resource import Resource
from arches.app.utils.betterJSONSerializer import JSONDeserializer, JSONSerializer
from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.models import VwLabelValue
from arches_lingo.utils.concept_builder import ConceptBuilder
from arches_querysets.models import SemanticResource


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
        max_edit_distance = request.GET.get(
            "maxEditDistance", self.default_sensitivity()
        )
        exact = request.GET.get("exact", False)
        page_number = request.GET.get("page", 1)
        items_per_page = request.GET.get("items", 25)

        if exact:
            concept_query = VwLabelValue.objects.filter(value=term).order_by(
                "concept_id"
            )
        elif term:
            try:
                concept_query = VwLabelValue.objects.fuzzy_search(
                    term, max_edit_distance
                )
            except ValueError as ve:
                return JSONErrorResponse(
                    title=_("Unable to perform search."),
                    message=ve.args[0],
                    status=HTTPStatus.BAD_REQUEST,
                )
        else:
            concept_query = VwLabelValue.objects.all().order_by("concept_id")
        concept_ids = concept_query.values_list("concept_id", flat=True).distinct()

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

    @staticmethod
    def default_sensitivity():
        """Remains to be seen whether the existing elastic sensitivity setting
        should be the fallback, but stub something out for now.
        This sensitivity setting is actually inversely related to edit distance,
        because it's prefix_length in elastic, not fuzziness, so invert it.
        """
        elastic_prefix_length = settings.SEARCH_TERM_SENSITIVITY
        if elastic_prefix_length <= 0:
            return 5
        if elastic_prefix_length >= 5:
            return 0
        return int(5 - elastic_prefix_length)


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
        Concept = SemanticResource.as_model("concept")

        if not concept_ids:
            # if scheme:
            #     if exclude == "true":
            #         concept_query = Concept.exclude(
            #             part_of_scheme__0__0__resourceId=scheme
            #         )
            #     else:
            #         concept_query = Concept.filter(
            #             part_of_scheme__0__0__resourceId=scheme
            #         )
            # else:
            concept_query = Concept.all()

            if term:
                filtering_concept_ids = VwLabelValue.objects.filter(
                    value__icontains=term
                ).values_list("concept_id", flat=True)
                concept_query = concept_query.filter(pk__in=filtering_concept_ids)

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
        def get_pref_label(labels, language):
            pref_label = {
                "display_value": "",
                "list_item_id": "",
            }
            for label in labels:
                if label["language_id"] == language and label["valuetype_id"] == "prefLabel":
                    pref_label["display_value"] = label["value"]
                    pref_label["list_item_id"] = label["list_item_id"]
                    break
            return pref_label

        concept_id = request.GET.get("concept")
        relationship_type = request.GET.get("type")
        language = get_language()
        Concept = SemanticResource.as_model("concept")

        concept = Concept.get(pk=concept_id)
        scheme_id = concept.aliased_data.part_of_scheme.aliased_data.part_of_scheme["resourceId"]
        
        if relationship_type == "associated":
            relationships = concept.aliased_data.relation_status
        elif relationship_type == "matched":
            relationships = concept.aliased_data.match_status

        return_data = []
        for relationship in relationships:
            data = JSONDeserializer().deserialize(JSONSerializer().serialize(relationship))
            aliased_data = JSONDeserializer().deserialize(
                JSONSerializer().serialize(relationship.aliased_data)
            )

            uri = None
            for node_alias, node_value in aliased_data.items():
                if node_value and type(node_value) == list:
                    resource_id = None
                    return_labels = []
                    if "resourceId" in node_value[0]:
                        for value in node_value:
                            resource_id = value["resourceId"]
                            resource = Resource.objects.get(pk=resource_id)
                            display_value = resource.descriptors[language]["name"]
                            value["display_value"] = display_value
                        if resource_id:
                            try:
                                concept = Concept.get(pk=resource_id)
                                if concept.aliased_data.uri:
                                    print("concept.aliased_data.uri", concept.aliased_data.uri)
                                    uri = concept.aliased_data.uri.aliased_data.uri_content
                                    print(uri)
                            except SemanticResource.DoesNotExist:
                                pass
                    elif "labels" in node_value[0]:
                        for value in node_value:                            
                            labels = value["labels"]
                            pref_label = get_pref_label(labels, language)
                            if pref_label["display_value"]:
                                return_labels.append(pref_label)
                        if len(return_labels) > 0:
                            aliased_data[node_alias] = return_labels

            if uri:
                aliased_data["uri"] = uri

            del data["data"]
            data["aliased_data"] = aliased_data
            data["scheme_id"] = scheme_id
            return_data.append(data)

        return JSONResponse(return_data)
