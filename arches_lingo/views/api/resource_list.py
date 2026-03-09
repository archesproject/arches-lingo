from django.utils.decorators import method_decorator
from django.views.generic import View

from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONResponse

from arches_lingo.utils.resource_list import (
    CONTRIBUTORS_GRAPH_SLUGS,
    SOURCES_GRAPH_SLUGS,
    get_paginated_resources,
)

DEFAULT_PAGE_SIZE = 25


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class PaginatedResourceListView(View):
    graph_slugs: list[str] = []

    def get(self, request):
        search_term = request.GET.get("search", "")
        limit = int(request.GET.get("limit", DEFAULT_PAGE_SIZE))
        offset = int(request.GET.get("offset", 0))

        data = get_paginated_resources(
            self.graph_slugs,
            search_term=search_term,
            limit=limit,
            offset=offset,
        )
        return JSONResponse(data)


class SourcesListView(PaginatedResourceListView):
    graph_slugs = SOURCES_GRAPH_SLUGS


class ContributorsListView(PaginatedResourceListView):
    graph_slugs = CONTRIBUTORS_GRAPH_SLUGS
