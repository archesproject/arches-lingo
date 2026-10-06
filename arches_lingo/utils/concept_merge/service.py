import uuid

from django.db import transaction

from arches_lingo.models import ConceptMatchCandidate, ConceptMerge
from arches_lingo.utils.concept_lifecycle import (
    delete_concept,
    index_concepts_in_transaction,
    retire_concept,
)
from arches_lingo.utils.concept_pair_decisions import (
    hand_pending_pairs_to_survivor,
    mark_pairs_settled,
)
from arches_lingo.utils.concept_merge.history import get_labels_by_concept_id
from arches_lingo.utils.concept_merge.tiles import (
    append_digital_objects_to_survivor,
    copy_tiles_to_survivor,
    demote_pref_label_tiles,
    write_exact_match_tiles,
)
from arches_lingo.utils.concept_merge.validation import (
    concept_is_writable,
    resolve_scheme_id,
)


def merge_concepts(survivor, absorbed, selections, user, user_is_lingo_admin=False):
    """Apply a validated merge and return its audit record.

    The concept the editor is viewing is the survivor; the concept they pick is
    absorbed. Selected tiles are copied from the absorbed concept onto the
    survivor, an exactMatch is recorded between the two so the absorbed
    concept's still-resolvable URI does not dead-end, and within a scheme the
    absorbed concept can be retired -- or, as a draft, deleted -- in the same
    transaction.
    """
    edit_transaction_id = uuid.uuid4()
    # Read up front: deleting a draft absorbed concept clears its pk.
    survivor_id = survivor.pk
    absorbed_id = absorbed.pk
    selected_tile_ids = selections.get("tile_selections") or []
    pref_label_demotion_tile_ids = {
        str(tile_id) for tile_id in selections.get("pref_label_demotions") or []
    }
    survivor_pref_label_demotion_tile_ids = {
        str(tile_id)
        for tile_id in selections.get("survivor_pref_label_demotions") or []
    }
    is_cross_scheme = resolve_scheme_id(survivor.pk) != resolve_scheme_id(absorbed.pk)
    should_delete_absorbed = bool(selections.get("delete_absorbed_concept"))
    should_retire_absorbed = bool(selections.get("retire_absorbed_concept"))
    absorbed_concept_labels = get_labels_by_concept_id([absorbed.pk])[str(absorbed.pk)]

    with transaction.atomic():
        # Demote first, so a surviving label that lost its language is already an
        # altLabel by the time the absorbed preferred label is copied across.
        demote_pref_label_tiles(
            survivor_pref_label_demotion_tile_ids, edit_transaction_id
        )
        copy_tiles_to_survivor(
            survivor,
            absorbed,
            selected_tile_ids,
            pref_label_demotion_tile_ids,
            edit_transaction_id,
        )
        append_digital_objects_to_survivor(
            survivor,
            absorbed,
            selections.get("digital_object_selections") or [],
            edit_transaction_id,
        )

        if selections.get("create_exact_match_tiles", True):
            write_exact_match_tiles(
                survivor,
                absorbed,
                edit_transaction_id,
                write_to_second=(
                    not should_delete_absorbed
                    and concept_is_writable(absorbed, user_is_lingo_admin)
                ),
            )

        # Removing inside the same transaction means a failure anywhere in the
        # merge rolls the retirement or deletion back with it.
        if should_retire_absorbed:
            retire_concept(
                absorbed,
                selections.get("retirement_strategy"),
                str(survivor.pk),
                edit_transaction_id,
            )
        elif should_delete_absorbed:
            delete_concept(
                absorbed,
                selections.get("retirement_strategy"),
                str(survivor.pk),
                edit_transaction_id,
            )

        concept_merge = ConceptMerge.objects.create(
            survivor_concept_id=survivor_id,
            absorbed_concept_id=absorbed_id,
            is_cross_scheme=is_cross_scheme,
            absorbed_concept_labels=absorbed_concept_labels,
            user=user if user is not None and user.is_authenticated else None,
            edit_transaction_id=edit_transaction_id,
            selections=selections,
        )

        mark_pairs_settled(
            [(survivor_id, absorbed_id)], ConceptMatchCandidate.STATUS_MERGED, user
        )
        if should_retire_absorbed or should_delete_absorbed:
            hand_pending_pairs_to_survivor(absorbed_id, survivor_id)

    # Indexed once the transaction commits, so a rolled-back merge stays out of
    # the index and both concepts are indexed as they finally stand.
    index_concepts_in_transaction(
        edit_transaction_id, additional_concept_ids=(survivor_id, absorbed_id)
    )
    return concept_merge
