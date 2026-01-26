import uuid

from django.db.models import Exists, OuterRef

from arches.app.functions.base import BaseFunction
from arches.app.models.models import (
    GraphModel,
    Node,
    ResourceIdentifier,
    ResourceInstance,
    TileModel,
)

from arches_lingo.models import ConceptIdentifierCounter
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

        part_of_scheme_node_id = (
            Node.objects.only("nodeid")
            .get(
                graph_id=concept_graph_id,
                alias="part_of_scheme",
            )
            .nodeid
        )

        related_concept_resource_instance_ids_queryset = (
            TileModel.objects.filter(
                data__contains={
                    str(part_of_scheme_node_id): [
                        {
                            "resourceId": str(scheme_resource_instance_id),
                        }
                    ],
                }
            )
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

        related_concepts_queryset = ResourceInstance.objects.filter(
            graph_id=concept_graph_id,
            resourceinstanceid__in=related_concept_resource_instance_ids_queryset,
        )

        if not related_concepts_queryset.exists():
            return

        is_scheme_promoting_to_active = (
            current_state.id
            in {
                DRAFT_RESOURCE_INSTANCE_LIFECYCLE_STATE_ID,
                EDITING_RESOURCE_INSTANCE_LIFECYCLE_STATE_ID,
            }
            and new_state.id == ACTIVE_RESOURCE_INSTANCE_LIFECYCLE_STATE_ID
        )

        if is_scheme_promoting_to_active:
            ConceptIdentifierCounter.objects.get_or_create(
                scheme_id=scheme_resource_instance_id
            )

            draft_concepts_queryset = related_concepts_queryset.filter(
                resource_instance_lifecycle_state_id=DRAFT_RESOURCE_INSTANCE_LIFECYCLE_STATE_ID
            )

            has_identifier_subquery = ResourceIdentifier.objects.filter(
                resourceid_id=OuterRef("resourceinstanceid"),
                source="arches-lingo",
            )

            draft_concept_resource_instance_ids_needing_identifier = list(
                draft_concepts_queryset.annotate(
                    has_identifier=Exists(has_identifier_subquery)
                )
                .filter(has_identifier=False)
                .values_list("resourceinstanceid", flat=True)
            )

            if draft_concept_resource_instance_ids_needing_identifier:
                first_allocated_number = allocate_concept_identifier_number(
                    scheme_resource_instance_id,
                    count=len(draft_concept_resource_instance_ids_needing_identifier),
                )

                allocated_identifier_by_concept_resource_instance_id = {
                    concept_resource_instance_id: str(first_allocated_number + index)
                    for index, concept_resource_instance_id in enumerate(
                        draft_concept_resource_instance_ids_needing_identifier
                    )
                }

                ResourceIdentifier.objects.bulk_create(
                    [
                        ResourceIdentifier(
                            resourceid_id=concept_resource_instance_id,
                            source="arches-lingo",
                            identifier=allocated_identifier_by_concept_resource_instance_id[
                                concept_resource_instance_id
                            ],
                        )
                        for concept_resource_instance_id in draft_concept_resource_instance_ids_needing_identifier
                    ],
                    ignore_conflicts=True,
                )

                identifier_content_node_id = (
                    Node.objects.only("nodeid")
                    .get(
                        graph_id=concept_graph_id,
                        alias="identifier_content",
                    )
                    .nodeid
                )

                identifier_content_tile_models = list(
                    TileModel.objects.filter(
                        resourceinstance_id__in=draft_concept_resource_instance_ids_needing_identifier,
                        data__has_key=str(identifier_content_node_id),
                    ).only("tileid", "data", "resourceinstance_id")
                )

                for tile_model in identifier_content_tile_models:
                    tile_model.data[str(identifier_content_node_id)] = (
                        allocated_identifier_by_concept_resource_instance_id[
                            tile_model.resourceinstance_id
                        ]
                    )

                if identifier_content_tile_models:
                    TileModel.objects.bulk_update(
                        identifier_content_tile_models,
                        ["data"],
                    )

        related_concepts_queryset.update(
            resource_instance_lifecycle_state_id=new_state.id
        )
