from http import HTTPStatus

from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models.system_settings import settings
from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_querysets.models import SemanticTile
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
        max_edit_distance = request.GET.get(
            "maxEditDistance", self.default_sensitivity()
        )
        exact = request.GET.get("exact", False)
        page_number = request.GET.get("page", 1)
        items_per_page = request.GET.get("items", 25)

        labels = SemanticTile.as_nodegroup("appellative_status", graph_slug="concept")

        if exact:
            concept_query = labels.filter(
                appellative_status_ascribed_name_content=term
            ).order_by("resourceinstance")
        elif term:
            try:
                concept_query = fuzzy_search(labels, term, max_edit_distance)
            except ValueError as ve:
                return JSONErrorResponse(
                    title=_("Unable to perform search."),
                    message=ve.args[0],
                    status=HTTPStatus.BAD_REQUEST,
                )
        else:
            concept_query = labels.order_by("resourceinstance")
        concept_ids = concept_query.values_list(
            "resourceinstance", flat=True
        ).distinct()

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
