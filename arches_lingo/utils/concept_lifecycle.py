import uuid

from arches.app.models.models import ResourceInstance, TileModel
from arches.app.models.tile import Tile

from arches_lingo.const import (
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    CLASSIFICATION_STATUS_NODEGROUP,
    TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
)


DRAFT_STATE_ID = uuid.UUID("0e7f8c6d-1f7b-4c2a-9a0c-2b9e0d6c8f11")
RETIRED_STATE_ID = uuid.UUID("9d2e1c0b-7a6b-4b3d-8c1a-0f2d9e6b0a7c")

STRATEGY_REPARENT = "reparent"
STRATEGY_DELETE_CHILDREN = "delete_children"
STRATEGY_ORPHAN = "orphan"

VALID_STRATEGIES = {STRATEGY_REPARENT, STRATEGY_DELETE_CHILDREN, STRATEGY_ORPHAN}


def get_narrower_ids(concept_id: str) -> set[str]:
    return {
        str(pk)
        for pk in TileModel.objects.filter(
            nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
            **{
                f"data__{CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID}__contains": [
                    {"resourceId": concept_id}
                ]
            },
        ).values_list("resourceinstance_id", flat=True)
    }


def get_broader_ids(concept_id: str) -> set[str]:
    broader_concept_ids = set()

    for classification_status_tile in TileModel.objects.filter(
        nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
        resourceinstance_id=concept_id,
    ):
        resource_references = (
            classification_status_tile.data.get(
                CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID
            )
            or []
        )

        for resource_reference in resource_references:
            if resource_reference.get("resourceId"):
                broader_concept_ids.add(resource_reference["resourceId"])

    return broader_concept_ids


def get_scheme_id_if_top_concept(concept_id: str) -> str | None:
    top_concept_of_tile = TileModel.objects.filter(
        nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
        resourceinstance_id=concept_id,
    ).first()

    if not top_concept_of_tile:
        return None

    resource_references = (
        top_concept_of_tile.data.get(TOP_CONCEPT_OF_NODE_AND_NODEGROUP) or []
    )
    return resource_references[0]["resourceId"] if resource_references else None


def get_all_descendant_ids(concept_id: str) -> set[str]:
    descendant_ids = set()
    frontier = {concept_id}

    while frontier:
        next_frontier = set()
        for ancestor_id in frontier:
            next_frontier.update(get_narrower_ids(ancestor_id))

        new_descendant_ids = next_frontier - descendant_ids - {concept_id}
        descendant_ids.update(new_descendant_ids)
        frontier = new_descendant_ids

    return descendant_ids


def reparent_children(concept_id: str, parent_ids: set[str], scheme_id: str | None):
    """Move children of concept_id up to its parents.

    If the concept being removed was itself a top concept, children with no
    remaining broader parent are promoted to top concepts of the same scheme.
    """
    child_classification_tiles = TileModel.objects.filter(
        nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
        **{
            f"data__{CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID}__contains": [
                {"resourceId": concept_id}
            ]
        },
    )
    for classification_tile in child_classification_tiles:
        existing_broader_references = (
            classification_tile.data.get(
                CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID
            )
            or []
        )
        updated_broader_references = [
            resource_reference
            for resource_reference in existing_broader_references
            if resource_reference.get("resourceId") != concept_id
        ]

        already_referenced_parent_ids = {
            resource_reference.get("resourceId")
            for resource_reference in updated_broader_references
        }
        for parent_id in parent_ids:
            if parent_id not in already_referenced_parent_ids:
                updated_broader_references.append({"resourceId": parent_id})

        if updated_broader_references:
            tile = Tile.objects.get(tileid=classification_tile.tileid)
            tile.data = {
                **tile.data,
                CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID: updated_broader_references,
            }
            tile.save(request=None)
        else:
            classification_tile.delete()

            if scheme_id:
                Tile(
                    resourceinstance_id=classification_tile.resourceinstance_id,
                    nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
                    data={
                        TOP_CONCEPT_OF_NODE_AND_NODEGROUP: [{"resourceId": scheme_id}]
                    },
                ).save(request=None)


def orphan_children(concept_id: str):
    """Remove concept_id as a broader parent from all its children."""
    child_classification_tiles = TileModel.objects.filter(
        nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
        **{
            f"data__{CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID}__contains": [
                {"resourceId": concept_id}
            ]
        },
    )

    for classification_tile in child_classification_tiles:
        existing_broader_references = (
            classification_tile.data.get(
                CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID
            )
            or []
        )

        updated_broader_references = [
            resource_reference
            for resource_reference in existing_broader_references
            if resource_reference.get("resourceId") != concept_id
        ]

        if updated_broader_references:
            tile = Tile.objects.get(tileid=classification_tile.tileid)
            tile.data = {
                **tile.data,
                CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID: updated_broader_references,
            }
            tile.save(request=None)
        else:
            classification_tile.delete()


def delete_concept(concept: ResourceInstance, strategy: str | None):
    concept_id = str(concept.pk)

    if strategy == STRATEGY_DELETE_CHILDREN:
        descendant_ids = get_all_descendant_ids(concept_id)
        if (
            ResourceInstance.objects.filter(pk__in=descendant_ids)
            .exclude(resource_instance_lifecycle_state_id=DRAFT_STATE_ID)
            .exists()
        ):
            raise ValueError(
                "One or more descendant concepts have been published and cannot be deleted."
            )
        ResourceInstance.objects.filter(pk__in=descendant_ids).delete()

    elif strategy == STRATEGY_REPARENT:
        reparent_children(
            concept_id,
            get_broader_ids(concept_id),
            get_scheme_id_if_top_concept(concept_id),
        )

    elif strategy == STRATEGY_ORPHAN:
        orphan_children(concept_id)

    concept.delete()


def retire_concept(concept: ResourceInstance, strategy: str | None):
    concept_id = str(concept.pk)

    if strategy == STRATEGY_DELETE_CHILDREN:
        descendant_ids = get_all_descendant_ids(concept_id)
        ResourceInstance.objects.filter(pk__in=descendant_ids).update(
            resource_instance_lifecycle_state_id=RETIRED_STATE_ID
        )

    elif strategy == STRATEGY_REPARENT:
        reparent_children(
            concept_id,
            get_broader_ids(concept_id),
            get_scheme_id_if_top_concept(concept_id),
        )

    elif strategy == STRATEGY_ORPHAN:
        orphan_children(concept_id)

    concept.resource_instance_lifecycle_state_id = RETIRED_STATE_ID
    concept.save(update_fields=["resource_instance_lifecycle_state"])
