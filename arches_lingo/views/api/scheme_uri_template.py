from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.utils.response import JSONResponse, JSONErrorResponse
from arches.app.views.api import APIBase

from arches_lingo.models import SchemeURITemplate


class SchemeURITemplateView(APIBase):
    def get(self, request, scheme_resource_instance_id):
        scheme_uri_template = SchemeURITemplate.objects.filter(
            scheme_id=scheme_resource_instance_id
        ).first()

        if not scheme_uri_template:
            return JSONErrorResponse(
                "SchemeURITemplate not found for the given scheme.",
                status=404,
            )

        return JSONResponse(scheme_uri_template)

    def post(self, request, scheme_resource_instance_id):
        request_json = JSONDeserializer().deserialize(request.body)

        current_scheme_uri_template = SchemeURITemplate.objects.filter(
            scheme_id=scheme_resource_instance_id
        ).first()

        url_template = request_json.get("url_template", "")

        if current_scheme_uri_template:
            current_scheme_uri_template.url_template = url_template
            current_scheme_uri_template.save(update_fields=["url_template"])

            return JSONResponse(current_scheme_uri_template)

        scheme_uri_template = SchemeURITemplate.objects.create(
            scheme_id=scheme_resource_instance_id,
            url_template=url_template,
        )

        return JSONResponse(scheme_uri_template)
