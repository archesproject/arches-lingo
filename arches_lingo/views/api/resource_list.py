from django.utils.decorators import method_decorator
from django.views.generic import View

from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONResponse

from arches_lingo.utils.resource_list import get_paginated_resource_summaries

SOURCES_GRAPH_SLUGS = ["textual_work"]
CONTRIBUTORS_GRAPH_SLUGS = ["person_system", "group"]

DEFAULT_PAGE_SIZE = 25


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class SourcesListView(View):
    def get(self, request):
        search_term = request.GET.get("search", "")
        limit = int(request.GET.get("limit", DEFAULT_PAGE_SIZE))
        offset = int(request.GET.get("offset", 0))

        data = get_paginated_resource_summaries(
            SOURCES_GRAPH_SLUGS,
            search_term=search_term,
            limit=limit,
            offset=offset,
        )
        return JSONResponse(data)


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class ContributorsListView(View):
    def get(self, request):
        search_term = request.GET.get("search", "")
        limit = int(request.GET.get("limit", DEFAULT_PAGE_SIZE))
        offset = int(request.GET.get("offset", 0))

        data = get_paginated_resource_summaries(
            CONTRIBUTORS_GRAPH_SLUGS,
            search_term=search_term,
            limit=limit,
            offset=offset,
        )
        return JSONResponse(data)
