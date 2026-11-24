from arches.app.models.models import ResourceIdentifier, ResourceInstance

from arches_lingo.const import SCHEMES_GRAPH_ID
from arches_lingo.models import ConceptMerge
from arches_lingo.utils.concept_lifecycle import (
    LOCKED_STATE_ID,
    PUBLISHED_STATE_ID,
    RETIRED_STATE_ID,
)
from arches_lingo.utils.concept_matching import get_scheme_ids_for_concepts

# OpenRefine never sends a session, so every caller sees the same public states.
# Retired resources are publicly dereferenceable but are not offered as matches.
RECONCILABLE_LIFECYCLE_STATE_IDS = frozenset({PUBLISHED_STATE_ID, LOCKED_STATE_ID})
# Searched so that a retired concept absorbed by a merge can lead to its survivor.
SEARCHED_LIFECYCLE_STATE_IDS = RECONCILABLE_LIFECYCLE_STATE_IDS | {RETIRED_STATE_ID}


def get_reconcilable_schemes():
    return ResourceInstance.objects.filter(
        graph_id=SCHEMES_GRAPH_ID,
        resource_instance_lifecycle_state_id__in=RECONCILABLE_LIFECYCLE_STATE_IDS,
    )


def get_reconcilable_scheme_ids():
    return {
        str(scheme_id)
        for scheme_id in get_reconcilable_schemes().values_list("pk", flat=True)
    }


def filter_public_concept_ids(concept_ids, scheme_ids=None):
    """Keep published, locked and retired concepts in ``scheme_ids``, which
    defaults to every reconcilable scheme."""
    if not concept_ids:
        return set()
    scheme_id_by_concept_id = get_scheme_ids_for_concepts(concept_ids)
    searchable_scheme_ids = (
        get_reconcilable_scheme_ids() if scheme_ids is None else scheme_ids
    )
    public_state_concept_ids = ResourceInstance.objects.filter(
        pk__in=concept_ids,
        resource_instance_lifecycle_state_id__in=SEARCHED_LIFECYCLE_STATE_IDS,
    ).values_list("pk", flat=True)
    return {
        str(concept_id)
        for concept_id in public_state_concept_ids
        if scheme_id_by_concept_id.get(str(concept_id)) in searchable_scheme_ids
    }


def resolve_reconcilable_scheme_id(scheme_identifier):
    """Return the id of the reconcilable scheme with this identifier, or None,
    also when several schemes share it, rather than serving one arbitrarily."""
    resource_ids = ResourceIdentifier.objects.filter(
        identifier=scheme_identifier,
        source="arches-lingo",
    ).values("resourceid")
    scheme_ids = list(
        get_reconcilable_schemes()
        .filter(pk__in=resource_ids)
        .values_list("pk", flat=True)
        .distinct()[:2]
    )
    return str(scheme_ids[0]) if len(scheme_ids) == 1 else None


def resolve_merge_survivors(concept_ids):
    """Map each concept absorbed by a merge to the last survivor in its chain.

    Concepts never absorbed are left out. A chain that loops back on itself
    stops at the last concept before the loop.
    """
    survivor_by_absorbed_id = {}
    unresolved_ids = {str(concept_id) for concept_id in concept_ids}
    while unresolved_ids:
        merges = ConceptMerge.objects.filter(
            absorbed_concept_id__in=unresolved_ids
        ).values_list("absorbed_concept_id", "survivor_concept_id")
        newly_found_survivors = {}
        # Ordered newest first, so the latest merge of a concept wins.
        for absorbed_id, survivor_id in merges:
            newly_found_survivors.setdefault(str(absorbed_id), str(survivor_id))
        survivor_by_absorbed_id.update(newly_found_survivors)
        unresolved_ids = set(newly_found_survivors.values()) - set(
            survivor_by_absorbed_id
        )

    final_survivor_by_concept_id = {}
    for concept_id in map(str, concept_ids):
        visited_ids = {concept_id}
        current_id = concept_id
        while (
            current_id in survivor_by_absorbed_id
            and survivor_by_absorbed_id[current_id] not in visited_ids
        ):
            current_id = survivor_by_absorbed_id[current_id]
            visited_ids.add(current_id)
        if current_id != concept_id:
            final_survivor_by_concept_id[concept_id] = current_id
    return final_survivor_by_concept_id
