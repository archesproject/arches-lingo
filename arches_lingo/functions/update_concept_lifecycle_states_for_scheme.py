import copy
import uuid

from django.db import transaction

from arches.app.functions.base import BaseFunction
from arches.app.models.models import (
    CardModel,
    CardXNodeXWidget,
    GraphModel,
    Node,
    ResourceIdentifier,
    ResourceInstance,
    TileModel,
)
from arches.app.models.tile import Tile

from arches_lingo.models import ConceptIdentifierCounter, SchemeURITemplate
from arches_lingo.utils.concept_identifier_allocator import (
    allocate_concept_identifier_number,
)


DRAFT_RESOURCE_INSTANCE_LIFECYCLE_STATE_ID = uuid.UUID(
    "0e7f8c6d-1f7b-4c2a-9a0c-2b9e0d6c8f11"
)
EDITING_RESOURCE_INSTANCE_LIFECYCLE_STATE_ID = uuid.UUID(
    "b3a6a0d2-2b5c-4c2f-9d6c-0c2a5b7d1e8f"
)
ACTIVE_RESOURCE_INSTANCE_LIFECYCLE_STATE_ID = uuid.UUID(
    "6b0f1a7b-5b3d-4b2a-8a5b-7c3a1b0f2d9e"
)
RETIRED_RESOURCE_INSTANCE_LIFECYCLE_STATE_ID = uuid.UUID(
    "9d2e1c0b-7a6b-4b3d-8c1a-0f2d9e6b0a7c"
)


details = {
    "name": "Update Concept Lifecycle States For Scheme",
    "functiontype": "lifecyclehandler",
    "type": "node",
    "description": "Updates concept lifecycle state tiles for all concepts in a scheme.",
    "defaultconfig": {},
    "component": "",
    "modulename": "update_concept_lifecycle_states_for_scheme.py",
    "classname": "UpdateConceptLifecycleStatesForScheme",
}


class UpdateConceptLifecycleStatesForScheme(BaseFunction):
    def on_update_lifecycle_state(
        self,
        resource_instance,
        current_state,
        new_state,
        request,
        context,
    ):
        scheme_resource_instance_id = resource_instance.resourceinstanceid

        concept_graph_id = (
            GraphModel.objects.only("graphid").get(slug="concept").graphid
        )

        related_non_retired_concepts_queryset = (
            self._get_related_non_retired_concepts_for_scheme(
                concept_graph_id=concept_graph_id,
                scheme_resource_instance_id=scheme_resource_instance_id,
            )
        )

        is_scheme_promoting_to_active = (
            current_state.id
            in {
                DRAFT_RESOURCE_INSTANCE_LIFECYCLE_STATE_ID,
                EDITING_RESOURCE_INSTANCE_LIFECYCLE_STATE_ID,
            }
            and new_state.id == ACTIVE_RESOURCE_INSTANCE_LIFECYCLE_STATE_ID
        )

        with transaction.atomic():
            if is_scheme_promoting_to_active:
                self._handle_scheme_promoted_to_active(
                    scheme_resource_instance_id=scheme_resource_instance_id,
                    request=request,
                )
                self._handle_draft_concepts_promoted_to_active(
                    scheme_resource_instance_id=scheme_resource_instance_id,
                    concept_graph_id=concept_graph_id,
                    related_non_retired_concepts_queryset=related_non_retired_concepts_queryset,
                    request=request,
                )
                self._recalculate_non_retired_concept_uris(
                    scheme_resource_instance_id=scheme_resource_instance_id,
                    concept_graph_id=concept_graph_id,
                    related_non_retired_concepts_queryset=related_non_retired_concepts_queryset,
                )

            if related_non_retired_concepts_queryset.exists():
                related_non_retired_concepts_queryset.update(
                    resource_instance_lifecycle_state_id=new_state.id
                )

    def _get_related_non_retired_concepts_for_scheme(
        self,
        concept_graph_id,
        scheme_resource_instance_id,
    ):
        part_of_scheme_node = Node.objects.only("nodeid", "nodegroup_id").get(
            graph_id=concept_graph_id,
            alias="part_of_scheme",
        )

        related_concept_resource_instance_ids_queryset = (
            TileModel.objects.filter(
                nodegroup_id=part_of_scheme_node.nodegroup_id,
                data__contains={
                    str(part_of_scheme_node.nodeid): [
                        {"resourceId": str(scheme_resource_instance_id)}
                    ],
                },
            )
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

        related_concepts_queryset = ResourceInstance.objects.filter(
            graph_id=concept_graph_id,
            resourceinstanceid__in=related_concept_resource_instance_ids_queryset,
        )

        return related_concepts_queryset.exclude(
            resource_instance_lifecycle_state_id=RETIRED_RESOURCE_INSTANCE_LIFECYCLE_STATE_ID
        )

    def _handle_scheme_promoted_to_active(
        self,
        scheme_resource_instance_id,
        request,
    ):
        scheme_uri_template_model, _ = SchemeURITemplate.objects.get_or_create(
            scheme_id=scheme_resource_instance_id
        )

        ConceptIdentifierCounter.objects.get_or_create(
            scheme_id=scheme_resource_instance_id
        )

        scheme_identifier_value = (
            ResourceIdentifier.objects.filter(
                resourceid_id=scheme_resource_instance_id,
                source="arches-lingo",
            )
            .values_list("identifier", flat=True)
            .first()
        )
        if not scheme_identifier_value:
            return

        template = scheme_uri_template_model.url_template
        if "<scheme_identifier>" not in template:
            return

        scheme_uri_value = template.replace(
            "<scheme_identifier>", scheme_identifier_value
        )

        scheme_graph_id = (
            ResourceInstance.objects.only("graph_id")
            .get(resourceinstanceid=scheme_resource_instance_id)
            .graph_id
        )

        uri_nodegroup_node = Node.objects.only("nodegroup_id").get(
            graph_id=scheme_graph_id,
            alias="uri",
        )

        uri_content_node = Node.objects.only("nodeid").get(
            graph_id=scheme_graph_id,
            alias="uri_content",
        )

        tile = Tile.objects.filter(
            resourceinstance_id=scheme_resource_instance_id,
            nodegroup_id=uri_nodegroup_node.nodegroup_id,
        ).first()

        if tile is None:
            tile = Tile.get_blank_tile_from_nodegroup_id(
                nodegroup_id=uri_nodegroup_node.nodegroup_id,
                resourceid=scheme_resource_instance_id,
                parenttile=None,
            )
            tile.data = self._get_nodegroup_data_with_widget_defaults(
                nodegroup_id=uri_nodegroup_node.nodegroup_id,
                resourceinstance_id=scheme_resource_instance_id,
            )

        tile.data[str(uri_content_node.nodeid)] = {
            "url": scheme_uri_value,
            "url_label": None,
        }
        tile.save(request=request, index=False)

    def _handle_draft_concepts_promoted_to_active(
        self,
        scheme_resource_instance_id,
        concept_graph_id,
        related_non_retired_concepts_queryset,
        request,
    ):
        draft_concept_resource_instance_ids = list(
            related_non_retired_concepts_queryset.filter(
                resource_instance_lifecycle_state_id=DRAFT_RESOURCE_INSTANCE_LIFECYCLE_STATE_ID
            )
            .select_for_update()
            .order_by("resourceinstanceid")
            .values_list("resourceinstanceid", flat=True)
        )
        if not draft_concept_resource_instance_ids:
            return

        identifier_nodegroup_node = Node.objects.only("nodegroup_id").get(
            graph_id=concept_graph_id,
            alias="identifier",
        )

        identifier_content_node = Node.objects.only("nodeid").get(
            graph_id=concept_graph_id,
            alias="identifier_content",
        )

        allocated_start_number = allocate_concept_identifier_number(
            scheme_resource_instance_id=scheme_resource_instance_id,
            count=len(draft_concept_resource_instance_ids),
        )

        resource_identifiers_to_create = []
        for concept_index, concept_resource_instance_id in enumerate(
            draft_concept_resource_instance_ids
        ):
            concept_identifier_number = allocated_start_number + concept_index
            concept_identifier_value = str(concept_identifier_number)

            resource_identifiers_to_create.append(
                ResourceIdentifier(
                    resourceid_id=concept_resource_instance_id,
                    identifier=concept_identifier_value,
                    source="arches-lingo",
                    identifier_type="",
                )
            )

        ResourceIdentifier.objects.bulk_create(resource_identifiers_to_create)

        default_identifier_tile_data = self._get_nodegroup_data_with_widget_defaults(
            nodegroup_id=identifier_nodegroup_node.nodegroup_id,
            resourceinstance_id=draft_concept_resource_instance_ids[0],
        )

        concept_tiles_to_create = []
        for concept_index, concept_resource_instance_id in enumerate(
            draft_concept_resource_instance_ids
        ):
            concept_identifier_number = allocated_start_number + concept_index
            concept_identifier_value = str(concept_identifier_number)

            concept_tile_data = copy.deepcopy(default_identifier_tile_data)
            concept_tile_data[str(identifier_content_node.nodeid)] = (
                concept_identifier_value
            )

            concept_tiles_to_create.append(
                TileModel(
                    resourceinstance_id=concept_resource_instance_id,
                    nodegroup_id=identifier_nodegroup_node.nodegroup_id,
                    parenttile_id=None,
                    data=concept_tile_data,
                    sortorder=0,
                    provisionaledits=None,
                )
            )

        TileModel.objects.bulk_create(concept_tiles_to_create)

    def _recalculate_non_retired_concept_uris(
        self,
        scheme_resource_instance_id,
        concept_graph_id,
        related_non_retired_concepts_queryset,
    ):
        scheme_uri_template_value = (
            SchemeURITemplate.objects.filter(scheme_id=scheme_resource_instance_id)
            .values_list("url_template", flat=True)
            .first()
        )

        scheme_identifier_value = (
            ResourceIdentifier.objects.filter(
                resourceid_id=scheme_resource_instance_id,
                source="arches-lingo",
            )
            .values_list("identifier", flat=True)
            .first()
        )
        if not scheme_identifier_value:
            return

        concept_resource_instance_ids = list(
            related_non_retired_concepts_queryset.values_list(
                "resourceinstanceid", flat=True
            )
        )
        if not concept_resource_instance_ids:
            return

        concept_identifier_by_resource_instance_id = dict(
            ResourceIdentifier.objects.filter(
                resourceid_id__in=concept_resource_instance_ids,
                source="arches-lingo",
            ).values_list("resourceid_id", "identifier")
        )
        if not concept_identifier_by_resource_instance_id:
            return

        uri_nodegroup_id = (
            Node.objects.only("nodegroup_id")
            .get(
                graph_id=concept_graph_id,
                alias="uri",
            )
            .nodegroup_id
        )

        uri_content_node_id_string = str(
            Node.objects.only("nodeid")
            .get(
                graph_id=concept_graph_id,
                alias="uri_content",
            )
            .nodeid
        )

        existing_uri_tiles = list(
            TileModel.objects.filter(
                resourceinstance_id__in=concept_resource_instance_ids,
                nodegroup_id=uri_nodegroup_id,
            ).only("tileid", "resourceinstance_id", "data")
        )

        existing_uri_tile_by_resource_instance_id = {
            existing_uri_tile.resourceinstance_id: existing_uri_tile
            for existing_uri_tile in existing_uri_tiles
        }

        default_uri_tile_data = self._get_nodegroup_data_with_widget_defaults(
            nodegroup_id=uri_nodegroup_id,
            resourceinstance_id=concept_resource_instance_ids[0],
        )

        uri_tiles_to_create = []
        uri_tiles_to_update = []

        for concept_resource_instance_id in concept_resource_instance_ids:
            concept_identifier_value = concept_identifier_by_resource_instance_id.get(
                concept_resource_instance_id
            )
            if not concept_identifier_value:
                continue

            desired_uri_value = scheme_uri_template_value.replace(
                "<scheme_identifier>", scheme_identifier_value
            ).replace("<concept_identifier>", concept_identifier_value)

            existing_uri_tile = existing_uri_tile_by_resource_instance_id.get(
                concept_resource_instance_id
            )

            if existing_uri_tile is None:
                new_tile_data = copy.deepcopy(default_uri_tile_data)
                new_tile_data[uri_content_node_id_string] = {
                    "url": desired_uri_value,
                    "url_label": None,
                }
                uri_tiles_to_create.append(
                    TileModel(
                        resourceinstance_id=concept_resource_instance_id,
                        nodegroup_id=uri_nodegroup_id,
                        parenttile_id=None,
                        data=new_tile_data,
                        sortorder=0,
                        provisionaledits=None,
                    )
                )
                continue

            existing_uri_value = (
                existing_uri_tile.data.get(uri_content_node_id_string) or {}
            ).get("url")

            if existing_uri_value == desired_uri_value:
                continue

            existing_uri_tile.data[uri_content_node_id_string] = {
                "url": desired_uri_value,
                "url_label": None,
            }
            uri_tiles_to_update.append(existing_uri_tile)

        if uri_tiles_to_create:
            TileModel.objects.bulk_create(uri_tiles_to_create)

        if uri_tiles_to_update:
            TileModel.objects.bulk_update(uri_tiles_to_update, ["data"])

    def _get_nodegroup_data_with_widget_defaults(
        self,
        nodegroup_id,
        resourceinstance_id,
    ):
        blank_tile = Tile.get_blank_tile_from_nodegroup_id(
            nodegroup_id=nodegroup_id,
            resourceid=resourceinstance_id,
            parenttile=None,
        )

        card_model = (
            CardModel.objects.filter(nodegroup_id=nodegroup_id).only("cardid").first()
        )
        if not card_model:
            return blank_tile.data

        for card_node_widget in CardXNodeXWidget.objects.filter(
            card_id=card_model.cardid
        ).only("node_id", "config"):
            widget_configuration = card_node_widget.config
            default_value = widget_configuration.get("defaultValue")

            if default_value is None:
                continue

            node_id = str(card_node_widget.node_id)
            if node_id in blank_tile.data and blank_tile.data[node_id] is None:
                blank_tile.data[node_id] = default_value

        return blank_tile.data
