import uuid

from django.db import transaction

from arches_lingo.models import ConceptMerge
from arches_lingo.utils.concept_lifecycle import (
    index_concepts_in_transaction,
    retire_concept,
)
from arches_lingo.utils.concept_merge.tiles import (
    append_digital_objects_to_survivor,
    copy_tiles_to_survivor,
    demote_pref_label_tiles,
    write_reciprocal_exact_match_tiles,
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
    absorbed concept can be retired in the same transaction.
    """
    edit_transaction_id = uuid.uuid4()
    selected_tile_ids = selections.get("tile_selections") or []
    pref_label_demotion_tile_ids = {
        str(tile_id) for tile_id in selections.get("pref_label_demotions") or []
    }
    survivor_pref_label_demotion_tile_ids = {
        str(tile_id)
        for tile_id in selections.get("survivor_pref_label_demotions") or []
    }
    is_cross_scheme = resolve_scheme_id(survivor.pk) != resolve_scheme_id(absorbed.pk)

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
            write_reciprocal_exact_match_tiles(
                survivor,
                absorbed,
                edit_transaction_id,
                write_to_absorbed=concept_is_writable(absorbed, user_is_lingo_admin),
            )

        # Retiring inside the same transaction means a failure anywhere in the
        # merge rolls the retirement back with it.
        if selections.get("retire_absorbed_concept"):
            retire_concept(
                absorbed,
                selections.get("retirement_strategy"),
                str(survivor.pk),
                edit_transaction_id,
            )

        concept_merge = ConceptMerge.objects.create(
            survivor_concept_id=survivor.pk,
            absorbed_concept_id=absorbed.pk,
            is_cross_scheme=is_cross_scheme,
            user=user if user is not None and user.is_authenticated else None,
            edit_transaction_id=edit_transaction_id,
            selections=selections,
        )

    # Indexed once the transaction commits, so a rolled-back merge stays out of
    # the index and both concepts are indexed as they finally stand.
    index_concepts_in_transaction(
        edit_transaction_id, additional_concept_ids=(survivor.pk, absorbed.pk)
    )
    return concept_merge
