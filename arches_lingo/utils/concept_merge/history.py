from django.db.models import Q

from arches.app.models.models import ResourceInstance

from arches_lingo.models import ConceptMerge
from arches_lingo.utils.concept_builder import ConceptBuilder


def get_labels_by_concept_id(concept_ids):
    """Each concept's labels, serialized the way the client picks a display name."""
    concept_ids = list({str(concept_id) for concept_id in concept_ids})
    label_builder = ConceptBuilder(concept_ids)
    return {
        concept_id: [
            label_builder.serialize_concept_label(label_tile)
            for label_tile in label_builder.labels[concept_id]
        ]
        for concept_id in concept_ids
    }


def get_concept_merge_history(concept_id):
    """Summarise every merge this concept took part in, newest first.

    Direction is expressed from this concept's point of view: "absorbed" means it
    took another concept's values in, "merged_into" means it was the one folded
    away. A merge across schemes only copies values out of the absorbed concept
    and leaves it in place, so it appears on the survivor's history alone.
    """
    merges = list(
        ConceptMerge.objects.filter(
            Q(survivor_concept_id=concept_id)
            | Q(absorbed_concept_id=concept_id, is_cross_scheme=False)
        )
    )
    if not merges:
        return []

    counterpart_ids = []
    for merge in merges:
        if str(merge.survivor_concept_id) == str(concept_id):
            counterpart_ids.append(str(merge.absorbed_concept_id))
        else:
            counterpart_ids.append(str(merge.survivor_concept_id))

    labels_by_concept_id = get_labels_by_concept_id(counterpart_ids)
    existing_concept_ids = {
        str(existing_id)
        for existing_id in ResourceInstance.objects.filter(
            pk__in=counterpart_ids
        ).values_list("pk", flat=True)
    }

    history = []
    for merge, counterpart_id in zip(merges, counterpart_ids):
        is_survivor = str(merge.survivor_concept_id) == str(concept_id)
        counterpart_labels = labels_by_concept_id.get(counterpart_id)
        # A draft deleted by the merge has no labels left to read.
        if not counterpart_labels and is_survivor:
            counterpart_labels = merge.absorbed_concept_labels
        history.append(
            {
                "id": merge.pk,
                "created": merge.created.isoformat(),
                "direction": "absorbed" if is_survivor else "merged_into",
                "is_cross_scheme": merge.is_cross_scheme,
                "counterpart_concept_id": counterpart_id,
                "counterpart_concept_labels": counterpart_labels or [],
                "counterpart_concept_exists": counterpart_id in existing_concept_ids,
            }
        )
    return history
