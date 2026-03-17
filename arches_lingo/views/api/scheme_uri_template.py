from http import HTTPStatus

from django.utils.translation import gettext as _
from arches.app.models.tile import Tile as TileModel
from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.utils.response import JSONResponse, JSONErrorResponse
from arches.app.views.api import APIBase

from arches_controlled_lists.models import ListItem

from arches_lingo.const import (
    NAMESPACE_NODEGROUP,
    NAMESPACE_NAME_NODE,
    NAMESPACE_TYPE_NODE,
    NAMESPACE_TYPE_LIST_ITEM_ID,
)
from arches_lingo.models import SchemeURITemplate
from arches_lingo.permissions import is_lingo_editor


class SchemeURITemplateView(APIBase):
    def dispatch(self, request, *args, **kwargs):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if not is_lingo_editor(request.user):
                return JSONErrorResponse(
                    title=_("Permission denied."),
                    message=_("You must be a Lingo editor to perform this action."),
                    status=HTTPStatus.FORBIDDEN,
                )
        return super().dispatch(request, *args, **kwargs)

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
        else:
            current_scheme_uri_template = SchemeURITemplate.objects.create(
                scheme_id=scheme_resource_instance_id,
                url_template=url_template,
            )

        namespace_tile_data = {
            NAMESPACE_NAME_NODE: url_template,
            NAMESPACE_TYPE_NODE: [
                ListItem.objects.get(pk=NAMESPACE_TYPE_LIST_ITEM_ID).build_tile_value()
            ],
        }

        namespace_tile, created = TileModel.objects.get_or_create(
            resourceinstance_id=scheme_resource_instance_id,
            nodegroup_id=NAMESPACE_NODEGROUP,
            defaults={"data": namespace_tile_data},
        )
        if not created:
            namespace_tile.data.update(namespace_tile_data)
            namespace_tile.save()

        return JSONResponse(current_scheme_uri_template)
