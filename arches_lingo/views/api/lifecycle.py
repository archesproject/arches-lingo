from django.views.generic import View

from arches.app.models.models import GraphModel, ResourceInstanceLifecycleState
from arches.app.utils.response import JSONResponse

from arches_lingo.const import CONCEPTS_GRAPH_ID, SCHEMES_GRAPH_ID
from arches_lingo.mixins.anonymous_access import AnonymousAccessMixin


class LifecycleStatesView(AnonymousAccessMixin, View):
    def get(self, request):
        lifecycle_ids = (
            GraphModel.objects.filter(
                graphid__in=[CONCEPTS_GRAPH_ID, SCHEMES_GRAPH_ID],
                resource_instance_lifecycle__isnull=False,
            )
            .values_list("resource_instance_lifecycle_id", flat=True)
            .distinct()
        )
        lifecycle_states = [
            {"id": str(state.id), "name": str(state.name)}
            for state in ResourceInstanceLifecycleState.objects.filter(
                resource_instance_lifecycle_id__in=lifecycle_ids
            ).distinct()
        ]
        return JSONResponse(lifecycle_states)
