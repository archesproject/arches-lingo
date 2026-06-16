from arches.app.models.models import ResourceInstance, TileModel

from arches_lingo.const import (
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
)
from arches_lingo.utils.concept_lifecycle import LOCKED_STATE_ID


def is_scheme_locked(scheme_pk) -> bool:
    return ResourceInstance.objects.filter(
        pk=scheme_pk,
        resource_instance_lifecycle_state_id=LOCKED_STATE_ID,
    ).exists()


def get_scheme_id_for_concept(concept_pk: str) -> str | None:
    tile = TileModel.objects.filter(
        resourceinstance_id=concept_pk,
        nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    ).first()
    if tile is None:
        return None
    data = tile.data.get(str(tile.nodegroup_id), [])
    if data:
        return data[0].get("resourceId")
    return None


def is_concept_in_locked_scheme(concept_pk: str) -> bool:
    scheme_id = get_scheme_id_for_concept(concept_pk)
    return bool(scheme_id and is_scheme_locked(scheme_id))
