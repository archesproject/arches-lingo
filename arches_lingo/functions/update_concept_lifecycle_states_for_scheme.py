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

from arches_controlled_lists.models import ListItem
from arches_lingo.const import (
    NAMESPACE_NODEGROUP,
    NAMESPACE_NAME_NODE,
    NAMESPACE_TYPE_NODE,
    NAMESPACE_TYPE_LIST_ITEM_ID,
    SCHEME_IDENTIFIER_NODEGROUP,
    SCHEME_IDENTIFIER_CONTENT_NODE,
)


from arches_lingo.models import ConceptIdentifierCounter, SchemeURITemplate
from arches_lingo.utils.concept_identifier_allocator import (
    allocate_concept_identifier_number,
)


IDENTIFIER_TYPE_LIST_ITEM_ID = uuid.UUID("d8ba08f9-b265-4288-9412-857c77fe2581")

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

CHUNK_SIZE = 2000


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
                url_template, scheme_identifier_value = (
                    self._handle_scheme_promoted_to_active(
                        scheme_resource_instance_id=scheme_resource_instance_id,
                        scheme_graph_id=resource_instance.graph_id,
                        request=request,
                    )
                )
                self._handle_draft_concepts_promoted_to_active(
                    scheme_resource_instance_id=scheme_resource_instance_id,
                    concept_graph_id=concept_graph_id,
                    related_non_retired_concepts_queryset=related_non_retired_concepts_queryset,
                    request=request,
                )
                self._recalculate_non_retired_concept_uris(
                    url_template=url_template,
                    scheme_identifier_value=scheme_identifier_value,
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
        scheme_graph_id,
        request,
    ):
        scheme_uri_template, _ = SchemeURITemplate.objects.get_or_create(
            scheme_id=scheme_resource_instance_id
        )

        namespace_type_value = [
            ListItem.objects.get(pk=NAMESPACE_TYPE_LIST_ITEM_ID).build_tile_value()
        ]
        namespace_tile, created = TileModel.objects.get_or_create(
            resourceinstance_id=scheme_resource_instance_id,
            nodegroup_id=NAMESPACE_NODEGROUP,
            defaults={
                "data": {
                    NAMESPACE_NAME_NODE: scheme_uri_template.url_template,
                    NAMESPACE_TYPE_NODE: namespace_type_value,
                }
            },
        )
        if not created:
            if not namespace_tile.data.get(NAMESPACE_NAME_NODE):
                namespace_tile.data[NAMESPACE_NAME_NODE] = (
                    scheme_uri_template.url_template
                )
            namespace_tile.data[NAMESPACE_TYPE_NODE] = namespace_type_value
            namespace_tile.save()

        concept_identifier_counter, _ = ConceptIdentifierCounter.objects.get_or_create(
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
            identifier_tile = TileModel.objects.filter(
                resourceinstance_id=scheme_resource_instance_id,
                nodegroup_id=SCHEME_IDENTIFIER_NODEGROUP,
            ).first()
            if identifier_tile:
                scheme_identifier_value = identifier_tile.data.get(
                    SCHEME_IDENTIFIER_CONTENT_NODE
                )
            if scheme_identifier_value:
                ResourceIdentifier.objects.create(
                    resourceid_id=scheme_resource_instance_id,
                    identifier=scheme_identifier_value,
                    source="arches-lingo",
                    identifier_type="identifier",
                )

        uses_shared_counter = (
            "<scheme_and_concept_counter>" in scheme_uri_template.url_template
        )

        scheme_uri_value = None
        if scheme_identifier_value:
            if (
                not uses_shared_counter
                and "<scheme_identifier>" in scheme_uri_template.url_template
            ):
                scheme_uri_value = (
                    scheme_uri_template.url_template.split("<scheme_identifier>")[0]
                    + scheme_identifier_value
                )
            elif uses_shared_counter and concept_identifier_counter.start_number != 1:
                if (
                    concept_identifier_counter.next_number
                    == concept_identifier_counter.start_number
                ):
                    concept_identifier_counter.next_number = (
                        concept_identifier_counter.start_number + 1
                    )
                    concept_identifier_counter.save(update_fields=["next_number"])
                scheme_uri_value = scheme_uri_template.url_template.replace(
                    "<scheme_identifier>", scheme_identifier_value
                ).replace(
                    "<scheme_and_concept_counter>",
                    str(concept_identifier_counter.start_number),
                )

        if scheme_uri_value:
            nodes = {
                node.alias: node
                for node in Node.objects.filter(
                    graph_id=scheme_graph_id,
                    alias__in=["uri", "uri_content"],
                )
            }
            uri_nodegroup_id = nodes["uri"].nodegroup_id
            uri_content_node_id = str(nodes["uri_content"].nodeid)

            tile = Tile.objects.filter(
                resourceinstance_id=scheme_resource_instance_id,
                nodegroup_id=uri_nodegroup_id,
            ).first()

            if tile is None:
                tile = Tile.get_blank_tile_from_nodegroup_id(
                    nodegroup_id=uri_nodegroup_id,
                    resourceid=scheme_resource_instance_id,
                    parenttile=None,
                )
                tile.data = self._get_nodegroup_data_with_widget_defaults(
                    nodegroup_id=uri_nodegroup_id,
                    resourceinstance_id=scheme_resource_instance_id,
                )

            tile.data[uri_content_node_id] = scheme_uri_value
            tile.save(request=request, index=False)

        return scheme_uri_template.url_template, scheme_identifier_value

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

        nodes = {
            node.alias: node
            for node in Node.objects.filter(
                graph_id=concept_graph_id,
                alias__in=["identifier", "identifier_content", "identifier_type"],
            )
        }
        identifier_nodegroup_id = nodes["identifier"].nodegroup_id
        identifier_content_node_id = str(nodes["identifier_content"].nodeid)
        identifier_type_node_id = str(nodes["identifier_type"].nodeid)

        identifier_type_list_item = ListItem.objects.get(
            pk=IDENTIFIER_TYPE_LIST_ITEM_ID
        )
        identifier_type_tile_value = [identifier_type_list_item.build_tile_value()]

        allocated_start_number = allocate_concept_identifier_number(
            scheme_resource_instance_id=scheme_resource_instance_id,
            count=len(draft_concept_resource_instance_ids),
        )

        default_identifier_tile_data = self._get_nodegroup_data_with_widget_defaults(
            nodegroup_id=identifier_nodegroup_id,
            resourceinstance_id=draft_concept_resource_instance_ids[0],
        )

        for chunk_start in range(
            0, len(draft_concept_resource_instance_ids), CHUNK_SIZE
        ):
            chunk_ids = draft_concept_resource_instance_ids[
                chunk_start : chunk_start + CHUNK_SIZE
            ]

            resource_identifiers_to_create = []
            concept_tiles_to_create = []

            for concept_index, concept_resource_instance_id in enumerate(
                chunk_ids, start=chunk_start
            ):
                concept_identifier_value = str(allocated_start_number + concept_index)

                resource_identifiers_to_create.append(
                    ResourceIdentifier(
                        resourceid_id=concept_resource_instance_id,
                        identifier=concept_identifier_value,
                        source="arches-lingo",
                        identifier_type="identifier",
                    )
                )

                concept_tile_data = copy.deepcopy(default_identifier_tile_data)
                concept_tile_data[identifier_content_node_id] = concept_identifier_value
                concept_tile_data[identifier_type_node_id] = identifier_type_tile_value

                concept_tiles_to_create.append(
                    TileModel(
                        resourceinstance_id=concept_resource_instance_id,
                        nodegroup_id=identifier_nodegroup_id,
                        parenttile_id=None,
                        data=concept_tile_data,
                        sortorder=0,
                        provisionaledits=None,
                    )
                )

            ResourceIdentifier.objects.bulk_create(resource_identifiers_to_create)
            TileModel.objects.bulk_create(concept_tiles_to_create)

    def _recalculate_non_retired_concept_uris(
        self,
        url_template,
        scheme_identifier_value,
        concept_graph_id,
        related_non_retired_concepts_queryset,
    ):
        if not scheme_identifier_value:
            return

        concept_resource_instance_ids = list(
            related_non_retired_concepts_queryset.values_list(
                "resourceinstanceid", flat=True
            )
        )
        if not concept_resource_instance_ids:
            return

        nodes = {
            node.alias: node
            for node in Node.objects.filter(
                graph_id=concept_graph_id,
                alias__in=["uri", "uri_content"],
            )
        }
        uri_nodegroup_id = nodes["uri"].nodegroup_id
        uri_content_node_id_string = str(nodes["uri_content"].nodeid)

        default_uri_tile_data = self._get_nodegroup_data_with_widget_defaults(
            nodegroup_id=uri_nodegroup_id,
            resourceinstance_id=concept_resource_instance_ids[0],
        )

        for chunk_start in range(0, len(concept_resource_instance_ids), CHUNK_SIZE):
            chunk_ids = concept_resource_instance_ids[
                chunk_start : chunk_start + CHUNK_SIZE
            ]

            chunk_identifier_by_resource_instance_id = dict(
                ResourceIdentifier.objects.filter(
                    resourceid_id__in=chunk_ids,
                    source="arches-lingo",
                ).values_list("resourceid_id", "identifier")
            )

            chunk_existing_tile_by_resource_instance_id = {
                tile.resourceinstance_id: tile
                for tile in TileModel.objects.filter(
                    resourceinstance_id__in=chunk_ids,
                    nodegroup_id=uri_nodegroup_id,
                ).only("tileid", "resourceinstance_id", "data")
            }

            uri_template_with_scheme = url_template.replace(
                "<scheme_identifier>", scheme_identifier_value
            )

            uri_tiles_to_create = []
            uri_tiles_to_update = []

            for concept_resource_instance_id in chunk_ids:
                concept_identifier_value = chunk_identifier_by_resource_instance_id.get(
                    concept_resource_instance_id
                )
                if not concept_identifier_value:
                    continue

                desired_uri_value = (
                    uri_template_with_scheme.replace(
                        "<concept_counter>", concept_identifier_value
                    )
                    .replace("<scheme_and_concept_counter>", concept_identifier_value)
                    .replace("<concept_identifier>", concept_identifier_value)
                )

                existing_uri_tile = chunk_existing_tile_by_resource_instance_id.get(
                    concept_resource_instance_id
                )

                if existing_uri_tile is None:
                    new_tile_data = copy.deepcopy(default_uri_tile_data)
                    new_tile_data[uri_content_node_id_string] = desired_uri_value
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

                existing_uri_value = existing_uri_tile.data.get(
                    uri_content_node_id_string
                )

                if existing_uri_value == desired_uri_value:
                    continue

                existing_uri_tile.data[uri_content_node_id_string] = desired_uri_value
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
