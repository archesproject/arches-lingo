from collections import defaultdict

from django.utils.translation import gettext as _

from arches.app.models.models import ResourceInstance, TileModel

from arches_lingo.const import (
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    CLASSIFICATION_STATUS_NODEGROUP,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_TYPE_NODE,
    PREF_LABEL_URI,
)
from arches_lingo.utils.concept_matching import get_scheme_ids_for_concepts
from arches_lingo.utils.reconciliation.labels import (
    choose_display_label,
    join_labels,
)
from arches_lingo.utils.reconciliation.manifest import list_reconcilable_schemes
from arches_lingo.utils.reconciliation.visibility import filter_public_concept_ids


def get_lifecycle_state_ids(concept_ids):
    return {
        str(concept_id): state_id
        for concept_id, state_id in ResourceInstance.objects.filter(
            pk__in=concept_ids
        ).values_list("pk", "resource_instance_lifecycle_state_id")
    }


def get_public_broader_ids_for_concepts(concept_ids, public_scheme_ids=None):
    """Return ``{concept_id: [broader_id, …]}``, leaving out broader concepts that
    are not public, such as a draft parent of a published concept."""
    broader_ids_by_concept_id = defaultdict(list)
    classification_tiles = TileModel.objects.filter(
        nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
        resourceinstance_id__in=concept_ids,
    ).values_list("resourceinstance_id", "data")
    for concept_id, tile_data in classification_tiles:
        for resource_reference in (
            tile_data.get(CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID) or []
        ):
            broader_id = resource_reference.get("resourceId")
            # A tile can name the same parent twice, and so can two tiles.
            if (
                broader_id
                and broader_id not in broader_ids_by_concept_id[str(concept_id)]
            ):
                broader_ids_by_concept_id[str(concept_id)].append(broader_id)

    public_broader_ids = filter_public_concept_ids(
        {
            broader_id
            for broader_ids in broader_ids_by_concept_id.values()
            for broader_id in broader_ids
        },
        public_scheme_ids,
    )
    return {
        concept_id: [
            broader_id for broader_id in broader_ids if broader_id in public_broader_ids
        ]
        for concept_id, broader_ids in broader_ids_by_concept_id.items()
    }


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


def get_pref_labels_for_concepts(concept_ids):
    """Return ``{concept_id: [(casefolded prefLabel, language), …]}``."""
    pref_labels_by_concept_id = defaultdict(list)
    label_tiles = TileModel.objects.filter(
        nodegroup_id=CONCEPT_NAME_NODEGROUP,
        resourceinstance_id__in=concept_ids,
    ).values_list("resourceinstance_id", "data")
    for concept_id, tile_data in label_tiles:
        label_types = tile_data.get(CONCEPT_NAME_TYPE_NODE) or []
        if not label_types or label_types[0].get("uri") != PREF_LABEL_URI:
            continue
        pref_labels_by_concept_id[str(concept_id)].append(
            (
                (tile_data.get(CONCEPT_NAME_CONTENT_NODE) or "").strip().casefold(),
                tile_data.get(CONCEPT_NAME_LANGUAGE_NODE),
            )
        )
    return pref_labels_by_concept_id


def summarize_concepts(concept_ids, target_language=None, public_scheme_ids=None):
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
    broader_ids_by_concept_id = get_public_broader_ids_for_concepts(
        concept_ids, public_scheme_ids
    )
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
        if broader_names:
            description = _("%(broader_concepts)s · %(scheme)s") % {
                "broader_concepts": join_labels(broader_names),
                "scheme": reconciliation_type["name"],
            }
        else:
            description = reconciliation_type["name"]
        summaries[concept_id] = {
            "name": display_label_by_concept_id.get(concept_id) or concept_id,
            "description": description,
            "type": [reconciliation_type],
        }
    return summaries
