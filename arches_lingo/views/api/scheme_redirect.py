from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.views import View

from arches.app.models.models import ResourceIdentifier


class SchemeConceptRedirectView(View):
    def get(self, request, scheme_identifier, concept_identifier):
        concept_resource_instance_id = (
            ResourceIdentifier.objects.filter(identifier=concept_identifier)
            .values_list("resourceid", flat=True)
            .first()
        )

        if concept_resource_instance_id is None:
            raise Http404()

        return HttpResponseRedirect(
            reverse(
                "concept",
                kwargs={"id": concept_resource_instance_id},
            )
        )
