from django.http import Http404, JsonResponse
from django.views import View

from arches.app.models.models import ResourceIdentifier, TileModel

from arches_lingo.const import URI_CONTENT_NODE, URI_NODEGROUP


class IdentifierResolveView(View):
    def get(self, request, **kwargs):
        identifier = kwargs.get("concept_identifier") or kwargs.get("scheme_identifier")
        resource_id = (
            ResourceIdentifier.objects.filter(
                identifier=identifier,
                source="arches-lingo",
            )
            .values_list("resourceid", flat=True)
            .first()
        )

        if resource_id is None:
            raise Http404()

        return JsonResponse({"resourceinstanceid": str(resource_id)})


class ConceptURILookupView(View):
    def get(self, request, **kwargs):
        uri = request.GET.get("uri", "").strip()
        if not uri:
            raise Http404()

        resource_id = (
            TileModel.objects.filter(
                nodegroup_id=URI_NODEGROUP,
                **{f"data__{URI_CONTENT_NODE}": uri},
            )
            .values_list("resourceinstance_id", flat=True)
            .first()
        )

        if resource_id is None:
            raise Http404()

        return JsonResponse({"resourceinstanceid": str(resource_id)})
