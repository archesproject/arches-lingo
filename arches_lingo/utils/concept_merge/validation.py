from http import HTTPStatus

from django.utils.translation import gettext as _

from arches.app.models.models import TileModel

from arches_lingo.const import CONCEPT_NAME_NODEGROUP, CONCEPTS_GRAPH_ID
from arches_lingo.utils.concept_lifecycle import (
    DRAFT_STATE_ID,
    EDITING_STATE_ID,
    LOCKED_STATE_ID,
    STRATEGY_DELETE_CHILDREN,
    STRATEGY_REPARENT_TO_SURVIVOR,
    VALID_STRATEGIES,
    get_all_descendant_ids,
    get_narrower_ids,
    get_scheme_id_if_top_concept,
    has_non_draft_descendants,
)
from arches_lingo.utils.concept_merge.rules import ConceptMergeGraph
from arches_lingo.utils.concept_merge.tiles import (
    get_depicted_digital_object_references,
)
from arches_lingo.utils.scheme_lock import get_scheme_id_for_concept, is_scheme_locked

# Retiring the absorbed concept is part of the merge, so reparent_to_survivor is
# offered alongside the strategies the standalone retire endpoint accepts.
VALID_MERGE_RETIREMENT_STRATEGIES = VALID_STRATEGIES | {STRATEGY_REPARENT_TO_SURVIVOR}

# Retirement strategies that break the hierarchy when the survivor sits beneath the
# absorbed concept: handing the children to the survivor would place the survivor's
# own ancestors under it, and retiring every descendant would retire the survivor.
STRATEGIES_UNAVAILABLE_BELOW_ABSORBED = frozenset(
    {STRATEGY_REPARENT_TO_SURVIVOR, STRATEGY_DELETE_CHILDREN}
)


class ConceptMergeError(Exception):
    """A merge that cannot proceed, carrying the response the view should send."""

    def __init__(self, title, message, status=HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.title = title
        self.message = message
        self.status = status


def resolve_scheme_id(concept_id):
    """Return the scheme a concept belongs to, whether by part_of_scheme or as a top concept."""
    return get_scheme_id_for_concept(str(concept_id)) or get_scheme_id_if_top_concept(
        str(concept_id)
    )


def lifecycle_state_permits_edit(concept, user_is_lingo_admin):
    """Locking a scheme moves its concepts into the Locked state, which forbids
    edits outright. A lingo admin may still edit a locked scheme, so for them the
    Locked state is no obstacle."""
    if concept.resource_instance_lifecycle_state_id == LOCKED_STATE_ID:
        return user_is_lingo_admin
    return concept.resource_instance_lifecycle_state.can_edit_resource_instances


def concept_is_writable(concept, user_is_lingo_admin):
    """Whether the merge may add tiles to this concept.

    A concept the merge only reads from needs no such permission, which is what
    lets a published or locked concept in another scheme be absorbed.
    """
    if not lifecycle_state_permits_edit(concept, user_is_lingo_admin):
        return False

    scheme_id = resolve_scheme_id(concept.pk)
    if scheme_id and is_scheme_locked(scheme_id) and not user_is_lingo_admin:
        return False

    return True


def is_removable_by_merge(concept, user_is_lingo_admin):
    """Within a scheme the absorbed concept is retired or, as a draft, deleted
    by the merge, so its state has to allow one of the two."""
    if concept.resource_instance_lifecycle_state_id in (
        EDITING_STATE_ID,
        DRAFT_STATE_ID,
    ):
        return True
    return (
        user_is_lingo_admin
        and concept.resource_instance_lifecycle_state_id == LOCKED_STATE_ID
    )


def validate_merge(survivor, absorbed, selections, user_is_lingo_admin):
    """Raise ConceptMergeError if this merge may not proceed."""
    if str(survivor.pk) == str(absorbed.pk):
        raise ConceptMergeError(
            _("Cannot merge"),
            _("A concept cannot be merged into itself."),
        )

    for concept in (survivor, absorbed):
        if str(concept.graph_id) != CONCEPTS_GRAPH_ID:
            raise ConceptMergeError(
                _("Cannot merge"),
                _("Both resources must be concepts."),
            )

    survivor_scheme_id = resolve_scheme_id(survivor.pk)
    absorbed_scheme_id = resolve_scheme_id(absorbed.pk)
    if not survivor_scheme_id or not absorbed_scheme_id:
        raise ConceptMergeError(
            _("Cannot merge"),
            _("Both concepts must belong to a scheme."),
        )

    is_cross_scheme = survivor_scheme_id != absorbed_scheme_id

    # Only the surviving concept is necessarily written to, so only its scheme
    # has to be unlocked. The absorbed concept's own scheme is checked when the
    # merge actually writes to it -- see concept_is_writable.
    if is_scheme_locked(survivor_scheme_id) and not user_is_lingo_admin:
        raise ConceptMergeError(
            _("Scheme is locked."),
            _("This concept's scheme is locked and cannot be edited."),
            status=HTTPStatus.LOCKED,
        )

    if not lifecycle_state_permits_edit(survivor, user_is_lingo_admin):
        raise ConceptMergeError(
            _("Cannot merge"),
            _("The surviving concept is in a state that cannot be edited."),
            status=HTTPStatus.CONFLICT,
        )

    # Across schemes the absorbed concept is only read from, so nothing about its
    # state stands in the way.
    if not is_cross_scheme and not is_removable_by_merge(absorbed, user_is_lingo_admin):
        raise ConceptMergeError(
            _("Cannot merge"),
            _(
                "Only a concept in the Editing or Draft state can be merged into "
                "another concept in the same scheme, because it must be retirable "
                "or deletable afterwards."
            ),
            status=HTTPStatus.CONFLICT,
        )

    validate_selected_tiles(
        absorbed, selections.get("tile_selections") or [], is_cross_scheme
    )
    validate_selected_digital_objects(
        absorbed, selections.get("digital_object_selections") or []
    )
    validate_pref_label_demotions(
        survivor,
        selections.get("survivor_pref_label_demotions") or [],
        _("Tile %(tileid)s is not a label of the surviving concept."),
    )
    validate_pref_label_demotions(
        absorbed,
        selections.get("pref_label_demotions") or [],
        _("Tile %(tileid)s is not a label of the absorbed concept."),
    )
    validate_absorbed_removal(survivor, absorbed, selections, is_cross_scheme)


def validate_absorbed_removal(survivor, absorbed, selections, is_cross_scheme=False):
    """Check retiring or deleting the absorbed concept as part of the merge.

    A draft has never been published, so it is deleted rather than retired;
    anything else is retired rather than deleted.
    """
    should_retire = bool(selections.get("retire_absorbed_concept"))
    should_delete = bool(selections.get("delete_absorbed_concept"))
    if not should_retire and not should_delete:
        return

    if should_retire and should_delete:
        raise ConceptMergeError(
            _("Cannot merge"),
            _("The absorbed concept can be retired or deleted, not both."),
        )

    # Either way the concept's children are rehomed, and every strategy for
    # doing so resolves within one scheme.
    if is_cross_scheme:
        raise ConceptMergeError(
            _("Cannot merge"),
            _(
                "A concept can only be retired or deleted by a merge within its "
                "own scheme. Merging across schemes leaves it in place."
            ),
        )

    is_draft = absorbed.resource_instance_lifecycle_state_id == DRAFT_STATE_ID
    if should_delete and not is_draft:
        raise ConceptMergeError(
            _("Cannot merge"),
            _("Only a draft concept can be deleted by a merge. Retire it instead."),
            status=HTTPStatus.CONFLICT,
        )
    if should_retire and is_draft:
        raise ConceptMergeError(
            _("Cannot merge"),
            _("A draft concept is deleted by a merge rather than retired."),
            status=HTTPStatus.CONFLICT,
        )

    retirement_strategy = selections.get("retirement_strategy")
    if (
        get_narrower_ids(str(absorbed.pk))
        and retirement_strategy not in VALID_MERGE_RETIREMENT_STRATEGIES
    ):
        raise ConceptMergeError(
            _("Strategy required"),
            _(
                "The concept being merged away has children. Choose how they "
                "should be handled before removing it."
            ),
        )

    if retirement_strategy in STRATEGIES_UNAVAILABLE_BELOW_ABSORBED and str(
        survivor.pk
    ) in get_all_descendant_ids(str(absorbed.pk)):
        raise ConceptMergeError(
            _("Cannot merge"),
            _(
                "The surviving concept sits beneath the concept being merged "
                "away, so its children cannot be attached to the surviving "
                "concept or removed with it. Attach them to their existing "
                "parents instead."
            ),
        )

    if (
        should_delete
        and retirement_strategy == STRATEGY_DELETE_CHILDREN
        and has_non_draft_descendants(str(absorbed.pk))
    ):
        raise ConceptMergeError(
            _("Cannot merge"),
            _(
                "One or more child concepts have been published, so they cannot "
                "be deleted along with the draft."
            ),
            status=HTTPStatus.CONFLICT,
        )


def validate_pref_label_demotions(concept, tile_ids, error_message):
    """Reject any demotion that does not name a label tile of the given concept."""
    demotable_tile_ids = {
        str(tileid)
        for tileid in TileModel.objects.filter(
            resourceinstance_id=concept.pk,
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
        ).values_list("tileid", flat=True)
    }

    for tile_id in tile_ids:
        if str(tile_id) not in demotable_tile_ids:
            raise ConceptMergeError(
                _("Cannot merge"), error_message % {"tileid": tile_id}
            )


def validate_selected_digital_objects(absorbed, selected_digital_object_ids):
    depicted_digital_object_ids = {
        str(reference.get("resourceId"))
        for reference in get_depicted_digital_object_references(absorbed.pk)
    }

    for digital_object_id in selected_digital_object_ids:
        if str(digital_object_id) not in depicted_digital_object_ids:
            raise ConceptMergeError(
                _("Cannot merge"),
                _("%(resourceid)s is not an image of the absorbed concept.")
                % {"resourceid": digital_object_id},
            )


def validate_selected_tiles(absorbed, selected_tile_ids, is_cross_scheme=False):
    merge_graph = ConceptMergeGraph()
    selectable_tiles_by_id = {
        str(tile.tileid): tile
        for tile in TileModel.objects.filter(
            resourceinstance_id=absorbed.pk,
            parenttile__isnull=True,
        )
    }

    for selected_tile_id in selected_tile_ids:
        source_tile = selectable_tiles_by_id.get(str(selected_tile_id))
        if source_tile is None:
            raise ConceptMergeError(
                _("Cannot merge"),
                _("Tile %(tileid)s is not a top-level tile of the absorbed concept.")
                % {"tileid": selected_tile_id},
            )

        nodegroup_alias = merge_graph.get_nodegroup_alias(source_tile.nodegroup_id)
        rule = merge_graph.get_rule(source_tile.nodegroup_id)
        if rule is None:
            raise ConceptMergeError(
                _("Cannot merge"),
                _("%(alias)s values cannot be copied between concepts.")
                % {"alias": nodegroup_alias},
            )

        if rule.is_reference_list:
            raise ConceptMergeError(
                _("Cannot merge"),
                _(
                    "Images are merged one at a time. Select them with "
                    "digital_object_selections rather than by tile."
                ),
            )

        if is_cross_scheme and rule.is_scheme_scoped:
            raise ConceptMergeError(
                _("Cannot merge"),
                _(
                    "%(alias)s values belong to a single scheme and cannot be "
                    "copied between concepts in different schemes."
                )
                % {"alias": nodegroup_alias},
            )
