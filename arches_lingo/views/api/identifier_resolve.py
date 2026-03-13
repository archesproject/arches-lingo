from django.http import Http404, JsonResponse
from django.views import View

from arches.app.models.models import ResourceIdentifier


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
