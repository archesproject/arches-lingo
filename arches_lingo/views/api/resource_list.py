from django.views.generic import View

from arches.app.models.system_settings import settings
from arches.app.utils.response import JSONResponse

from arches_lingo.mixins.anonymous_access import AnonymousAccessMixin
from arches_lingo.utils.resource_list import get_paginated_resource_summaries

SOURCES_GRAPH_SLUGS = ["textual_work"]
CONTRIBUTORS_GRAPH_SLUGS = ["person_system", "group"]


class SourcesListView(AnonymousAccessMixin, View):
    def get(self, request):
        search_term = request.GET.get("search", "")
        limit = int(request.GET.get("limit", settings.RESOURCE_LIST_PAGE_SIZE))
        offset = int(request.GET.get("offset", 0))

        data = get_paginated_resource_summaries(
            SOURCES_GRAPH_SLUGS,
            search_term=search_term,
            limit=limit,
            offset=offset,
        )
        return JSONResponse(data)


class ContributorsListView(AnonymousAccessMixin, View):
    def get(self, request):
        search_term = request.GET.get("search", "")
        limit = int(request.GET.get("limit", settings.RESOURCE_LIST_PAGE_SIZE))
        offset = int(request.GET.get("offset", 0))

        data = get_paginated_resource_summaries(
            CONTRIBUTORS_GRAPH_SLUGS,
            search_term=search_term,
            limit=limit,
            offset=offset,
        )
        return JSONResponse(data)
