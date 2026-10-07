from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.utils.response import JSONResponse, JSONErrorResponse
from arches.app.views.api import APIBase

from arches_lingo.mixins.permissions import LingoAdminWriteMixin
from arches_lingo.models import SchemeAttribution


class SchemeAttributionView(LingoAdminWriteMixin, APIBase):
    def get(self, request, scheme_resource_instance_id):
        scheme_attribution = SchemeAttribution.objects.filter(
            scheme_id=scheme_resource_instance_id
        ).first()

        if not scheme_attribution:
            return JSONErrorResponse(
                "SchemeAttribution not found for the given scheme.",
                status=404,
            )

        return JSONResponse(scheme_attribution)

    def post(self, request, scheme_resource_instance_id):
        request_json = JSONDeserializer().deserialize(request.body)

        current_scheme_attribution = SchemeAttribution.objects.filter(
            scheme_id=scheme_resource_instance_id
        ).first()

        attribution = request_json.get("attribution", "")

        if current_scheme_attribution:
            current_scheme_attribution.attribution = attribution
            current_scheme_attribution.save(update_fields=["attribution"])
        else:
            current_scheme_attribution = SchemeAttribution.objects.create(
                scheme_id=scheme_resource_instance_id,
                attribution=attribution,
            )

        return JSONResponse(current_scheme_attribution)
