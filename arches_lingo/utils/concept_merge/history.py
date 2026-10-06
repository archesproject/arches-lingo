from django.db.models import Q

from arches_lingo.models import ConceptMerge
from arches_lingo.utils.concept_builder import ConceptBuilder


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

    # Labels rather than the resource descriptor, so the client can pick the best
    # one for the reader's language the same way every other concept name is chosen.
    label_builder = ConceptBuilder(list(set(counterpart_ids)))
    labels_by_concept_id = {
        counterpart_id: [
            label_builder.serialize_concept_label(label_tile)
            for label_tile in label_builder.labels[counterpart_id]
        ]
        for counterpart_id in set(counterpart_ids)
    }

    history = []
    for merge, counterpart_id in zip(merges, counterpart_ids):
        is_survivor = str(merge.survivor_concept_id) == str(concept_id)
        history.append(
            {
                "id": merge.pk,
                "created": merge.created.isoformat(),
                "direction": "absorbed" if is_survivor else "merged_into",
                "is_cross_scheme": merge.is_cross_scheme,
                "counterpart_concept_id": counterpart_id,
                "counterpart_concept_labels": labels_by_concept_id.get(
                    counterpart_id, []
                ),
            }
        )
    return history
