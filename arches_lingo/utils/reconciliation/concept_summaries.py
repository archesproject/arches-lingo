from collections import defaultdict

from arches.app.models.models import ResourceInstance, TileModel

from arches_lingo.const import (
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    CLASSIFICATION_STATUS_NODEGROUP,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_TYPE_NODE,
)
from arches_lingo.utils.concept_matching import get_scheme_ids_for_concepts
from arches_lingo.utils.reconciliation.labels import choose_display_label
from arches_lingo.utils.reconciliation.manifest import list_reconcilable_schemes


def get_lifecycle_state_ids(concept_ids):
    return {
        str(concept_id): state_id
        for concept_id, state_id in ResourceInstance.objects.filter(
            pk__in=concept_ids
        ).values_list("pk", "resource_instance_lifecycle_state_id")
    }


def get_broader_ids_for_concepts(concept_ids):
    broader_ids_by_concept_id = defaultdict(list)
    classification_tiles = TileModel.objects.filter(
        nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
        resourceinstance_id__in=concept_ids,
    ).values_list("resourceinstance_id", "data")
    for concept_id, tile_data in classification_tiles:
        for resource_reference in (
            tile_data.get(CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID) or []
        ):
            if resource_reference.get("resourceId"):
                broader_ids_by_concept_id[str(concept_id)].append(
                    resource_reference["resourceId"]
                )
    return broader_ids_by_concept_id


def get_display_labels_for_concepts(concept_ids, target_language=None):
    label_tiles_by_concept_id = defaultdict(list)
    label_tiles = TileModel.objects.filter(
        nodegroup_id=CONCEPT_NAME_NODEGROUP,
        resourceinstance_id__in=concept_ids,
    ).values_list("resourceinstance_id", "data")
    for concept_id, tile_data in label_tiles:
        label_tiles_by_concept_id[str(concept_id)].append(tile_data)
    return {
        concept_id: choose_display_label(
            concept_label_tiles,
            CONCEPT_NAME_CONTENT_NODE,
            CONCEPT_NAME_TYPE_NODE,
            CONCEPT_NAME_LANGUAGE_NODE,
            target_language,
        )
        for concept_id, concept_label_tiles in label_tiles_by_concept_id.items()
    }


def summarize_concepts(concept_ids, target_language=None):
    """Return ``{concept_id: {name, description, type}}`` in a fixed number of queries.

    The description names the broader concepts and the scheme, which is what
    tells homographs apart in OpenRefine's candidate list. Concepts outside a
    reconcilable scheme are left out.
    """
    if not concept_ids:
        return {}

    scheme_id_by_concept_id = get_scheme_ids_for_concepts(concept_ids)
    reconciliation_type_by_scheme_id = {
        reconciliation_type["id"]: reconciliation_type
        for reconciliation_type in list_reconcilable_schemes(
            set(scheme_id_by_concept_id.values())
        )
    }
    broader_ids_by_concept_id = get_broader_ids_for_concepts(concept_ids)
    all_broader_ids = {
        broader_id
        for broader_ids in broader_ids_by_concept_id.values()
        for broader_id in broader_ids
    }
    display_label_by_concept_id = get_display_labels_for_concepts(
        set(concept_ids) | all_broader_ids, target_language
    )

    summaries = {}
    for concept_id in concept_ids:
        reconciliation_type = reconciliation_type_by_scheme_id.get(
            scheme_id_by_concept_id.get(concept_id)
        )
        if reconciliation_type is None:
            continue
        broader_names = sorted(
            display_label_by_concept_id[broader_id]
            for broader_id in broader_ids_by_concept_id.get(concept_id, [])
            if display_label_by_concept_id.get(broader_id)
        )
        description_parts = [", ".join(broader_names)] if broader_names else []
        description_parts.append(reconciliation_type["name"])
        summaries[concept_id] = {
            "name": display_label_by_concept_id.get(concept_id) or concept_id,
            "description": " · ".join(description_parts),
            "type": [reconciliation_type],
        }
    return summaries
