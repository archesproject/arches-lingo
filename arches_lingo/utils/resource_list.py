from django.db.models import Q

from arches.app.models.models import ResourceInstance, ResourceXResource


def get_resource_reference_count(resource_id):
    return ResourceXResource.objects.filter(
        Q(from_resource_id=resource_id) | Q(to_resource_id=resource_id)
    ).count()


def get_paginated_resource_summaries(graph_slugs, search_term="", limit=25, offset=0):
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
