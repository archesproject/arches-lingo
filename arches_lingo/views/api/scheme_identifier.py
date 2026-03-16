from arches.app.models.models import ResourceIdentifier
from arches.app.models.tile import Tile as TileModel
from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.utils.response import JSONResponse, JSONErrorResponse
from arches.app.views.api import APIBase

from arches_controlled_lists.models import ListItem

from arches_lingo.const import (
    SCHEME_IDENTIFIER_NODEGROUP,
    SCHEME_IDENTIFIER_CONTENT_NODE,
    SCHEME_IDENTIFIER_LABEL_NODE,
    SCHEME_IDENTIFIER_TYPE_NODE,
    SCHEME_IDENTIFIER_TYPE_LIST_ITEM_ID,
)


class SchemeIdentifierView(APIBase):
    def post(self, request, scheme_resource_instance_id):
        request_json = JSONDeserializer().deserialize(request.body)
        identifier = request_json.get("identifier", "")

        if not identifier:
            return JSONErrorResponse("identifier is required", status=400)

        resource_identifier, _ = ResourceIdentifier.objects.update_or_create(
            resourceid_id=scheme_resource_instance_id,
            source="arches-lingo",
            defaults={
                "identifier": identifier,
                "identifier_type": "identifier",
            },
        )

        tile_data = {
            SCHEME_IDENTIFIER_CONTENT_NODE: identifier,
            SCHEME_IDENTIFIER_LABEL_NODE: None,
            SCHEME_IDENTIFIER_TYPE_NODE: [
                ListItem.objects.get(
                    pk=SCHEME_IDENTIFIER_TYPE_LIST_ITEM_ID
                ).build_tile_value()
            ],
        }

        tile, created = TileModel.objects.get_or_create(
            resourceinstance_id=scheme_resource_instance_id,
            nodegroup_id=SCHEME_IDENTIFIER_NODEGROUP,
            defaults={"data": tile_data},
        )
        if not created:
            tile.data = tile_data
            tile.save()

        return JSONResponse(
            {"id": resource_identifier.id, "identifier": resource_identifier.identifier}
        )
