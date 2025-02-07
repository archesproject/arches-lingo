from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from arches.app.utils.decorators import group_required
from django.views import View
from django.utils.translation import get_language
from arches.app.models.models import Node, ResourceInstance, GraphModel
from arches.app.utils.response import JSONResponse
from arches.app.utils.betterJSONSerializer import JSONDeserializer

from arches.app.utils.decorators import can_edit_resource_instance


@method_decorator(can_edit_resource_instance, name="dispatch")
class RelatableResourcesView(View):
    def get(self, request, graph_slug, node_alias):
        node = Node.objects.get(
            name=node_alias,
            graph__slug=graph_slug,
            graph__is_active=True,
            graph__publication__isnull=False,
        )
        page_number = request.GET.get("page", 1)
        items_per_page = request.GET.get("items", 25)

        config = JSONDeserializer().deserialize(node.config.value)
        graphs = [graph["graphid"] for graph in config.get("graphs", [])]

        graph_models = GraphModel.objects.filter(graphid__in=graphs).values(
            "name", "graphid", "slug"
        )

        resources = ResourceInstance.objects.filter(graph_id__in=graphs).order_by(
            "descriptors__{}__name".format(get_language())
        )

        paginator = Paginator(resources, items_per_page)
        page_object = paginator.get_page(page_number)
        language = get_language()
        data = [
            {
                "resourceinstanceid": resource.resourceinstanceid,
                "display_value": resource.descriptors[language]["name"],
            }
            for resource in page_object
        ]

        return JSONResponse(
            {
                "graphs": graph_models,
                "current_page": paginator.get_page(page_number).number,
                "total_pages": paginator.num_pages,
                "results_per_page": paginator.per_page,
                "total_results": paginator.count,
                "data": data,
            }
        )
