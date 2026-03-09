from arches.app.models.models import ResourceInstance

SOURCES_GRAPH_SLUGS = ["textual_work"]
CONTRIBUTORS_GRAPH_SLUGS = ["person_system", "group"]


def get_paginated_resources(graph_slugs, search_term="", limit=25, offset=0):
    """Return a paginated, optionally name-filtered list of resources
    belonging to the given graph slugs.

    Returns a dict with ``count`` (total matching) and ``results``
    (the current page of resource summaries).
    """
    queryset = ResourceInstance.objects.filter(
        graph__slug__in=graph_slugs,
    ).select_related("graph")

    if search_term:
        queryset = queryset.filter(name__icontains=search_term)

    total_count = queryset.count()
    resources = queryset.order_by("name")[offset : offset + limit]

    results = [
        {
            "resourceinstanceid": str(resource.resourceinstanceid),
            "display_name": str(resource.name) if resource.name else "",
            "graph_slug": resource.graph.slug,
            "graph_name": resource.graph.name,
        }
        for resource in resources
    ]

    return {
        "count": total_count,
        "results": results,
    }
