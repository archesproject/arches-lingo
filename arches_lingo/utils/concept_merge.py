"""Business logic for merging one concept into another.

The concept the editor is viewing is the *survivor*; the concept they pick is
*absorbed*. Selected tiles are copied from the absorbed concept onto the
survivor, an exactMatch is recorded in both directions so the absorbed
concept's still-resolvable URI does not dead-end, and an audit record is
written. Retiring the absorbed concept is a separate step, handled by the
existing concept lifecycle endpoints.
"""

import copy
import uuid
from collections import defaultdict
from http import HTTPStatus

from django.db import transaction
from django.utils.translation import gettext as _

from arches.app.models.models import NodeGroup, TileModel
from arches.app.models.tile import Tile

from arches_controlled_lists.models import ListItem

from arches_lingo.const import (
    ALT_LABEL_LIST_ITEM_ID,
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    CLASSIFICATION_STATUS_NODEGROUP,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_TYPE_NODE,
    CONCEPTS_GRAPH_ID,
    EXACT_MATCH_LIST_ITEM_ID,
    MATCH_STATUS_COMPARATE_NODE,
    MATCH_STATUS_NODEGROUP,
    MATCH_STATUS_RELATION_NODE,
    RELATION_STATUS_ASCRIBED_COMPARATE_NODEID,
    RELATION_STATUS_ASCRIBED_RELATION_NODEID,
    RELATION_STATUS_NODEGROUP,
    STATEMENT_CONTENT_NODE,
    STATEMENT_LANGUAGE_NODE,
    STATEMENT_NODEGROUP,
    STATEMENT_TYPE_NODE,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)
from arches_lingo.models import ConceptMerge
from arches_lingo.utils.concept_lifecycle import (
    EDITING_STATE_ID,
    get_scheme_id_if_top_concept,
)
from arches_lingo.utils.scheme_lock import get_scheme_id_for_concept, is_scheme_locked

SINGLE_CARDINALITY = "1"

# Nodegroups an editor may never pull across from the absorbed concept.
# uri is cardinality-1 and ConceptURILookupView resolves by exact tile match, so
# two concepts must never carry the same one. identifier is allocated per scheme
# by ConceptIdentifierCounter and would misrepresent the survivor. part_of_scheme
# is always identical, since merges are restricted to a single scheme.
EXCLUDED_NODEGROUP_ALIASES = frozenset({"uri", "identifier", "part_of_scheme"})

# Node values that together identify a tile's content, used to skip copying a
# tile the survivor already holds. Nodegroups absent here are never deduplicated.
IDENTITY_NODES_BY_NODEGROUP = {
    CONCEPT_NAME_NODEGROUP: (
        CONCEPT_NAME_CONTENT_NODE,
        CONCEPT_NAME_LANGUAGE_NODE,
        CONCEPT_NAME_TYPE_NODE,
    ),
    STATEMENT_NODEGROUP: (
        STATEMENT_CONTENT_NODE,
        STATEMENT_LANGUAGE_NODE,
        STATEMENT_TYPE_NODE,
    ),
    CLASSIFICATION_STATUS_NODEGROUP: (
        CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    ),
    RELATION_STATUS_NODEGROUP: (
        RELATION_STATUS_ASCRIBED_COMPARATE_NODEID,
        RELATION_STATUS_ASCRIBED_RELATION_NODEID,
    ),
    MATCH_STATUS_NODEGROUP: (
        MATCH_STATUS_COMPARATE_NODE,
        MATCH_STATUS_RELATION_NODE,
    ),
}


class ConceptMergeError(Exception):
    """A merge that cannot proceed, carrying the response the view should send."""

    def __init__(self, title, message, status=HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.title = title
        self.message = message
        self.status = status


def get_concept_nodegroups_by_id():
    return {
        str(nodegroup.pk): nodegroup
        for nodegroup in NodeGroup.objects.filter(
            grouping_node__graph_id=CONCEPTS_GRAPH_ID
        ).select_related("grouping_node")
    }


def resolve_scheme_id(concept_id):
    """Return the scheme a concept belongs to, whether by part_of_scheme or as a top concept."""
    return get_scheme_id_for_concept(str(concept_id)) or get_scheme_id_if_top_concept(
        str(concept_id)
    )


def get_concept_uri(concept_id):
    uri_tile = TileModel.objects.filter(
        resourceinstance_id=concept_id,
        nodegroup_id=URI_NODEGROUP,
    ).first()
    return uri_tile.data.get(URI_CONTENT_NODE) if uri_tile else None


def normalize_node_value(node_value):
    """Reduce a node value to something comparable across tiles.

    Resource-instance and reference values carry per-tile bookkeeping alongside
    the value itself, so only the identifying part of each entry is kept.
    """
    if not isinstance(node_value, list):
        return node_value

    normalized_entries = []
    for entry in node_value:
        if isinstance(entry, dict):
            normalized_entries.append(entry.get("resourceId") or entry.get("uri"))
        else:
            normalized_entries.append(entry)
    return tuple(normalized_entries)


def build_tile_identity_key(nodegroup_id, tile_data):
    identity_node_ids = IDENTITY_NODES_BY_NODEGROUP.get(str(nodegroup_id))
    if not identity_node_ids:
        return None
    return tuple(
        normalize_node_value(tile_data.get(node_id)) for node_id in identity_node_ids
    )


def get_list_item_tile_value(list_item_id):
    return ListItem.objects.get(pk=list_item_id).build_tile_value()


def build_copied_tile_data(source_tile, should_demote_pref_label, alt_label_tile_value):
    tile_data = copy.deepcopy(source_tile.data)
    if should_demote_pref_label:
        tile_data[CONCEPT_NAME_TYPE_NODE] = [alt_label_tile_value]
    return tile_data


def create_tile_on_concept(
    concept_id, nodegroup_id, tile_data, parent_tile_id, edit_transaction_id
):
    """Save a tile through the Tile proxy so datatypes and graph functions run.

    Tiles are saved without a user because Tile.save() diverts data into
    provisional edits for any user who is not a resource reviewer, which would
    leave the merged values invisible. The merging user is recorded on the
    ConceptMerge instead, and edit log rows are grouped by transaction id.
    """
    tile = Tile(
        resourceinstance_id=concept_id,
        nodegroup_id=nodegroup_id,
        parenttile_id=parent_tile_id,
        data=tile_data,
    )
    tile.save(request=None, transaction_id=edit_transaction_id)
    return tile


def overwrite_single_cardinality_tile(
    concept_id, nodegroup_id, tile_data, edit_transaction_id
):
    """Replace the survivor's existing tile data in place, keeping its tileid.

    Any child tiles beneath it belong to the value being replaced, so they are
    deleted before the caller copies the absorbed concept's own children across.
    """
    existing_tile = TileModel.objects.filter(
        resourceinstance_id=concept_id,
        nodegroup_id=nodegroup_id,
    ).first()

    if existing_tile is None:
        return create_tile_on_concept(
            concept_id, nodegroup_id, tile_data, None, edit_transaction_id
        )

    for child_tile in Tile.objects.filter(parenttile_id=existing_tile.tileid):
        child_tile.delete(request=None)

    tile = Tile.objects.get(tileid=existing_tile.tileid)
    tile.data = tile_data
    tile.save(request=None, transaction_id=edit_transaction_id)
    return tile


def copy_child_tiles(
    source_parent_tile,
    target_parent_tile,
    source_child_tiles_by_parent_id,
    edit_transaction_id,
):
    copied_tiles = []
    for source_child_tile in source_child_tiles_by_parent_id.get(
        str(source_parent_tile.tileid), []
    ):
        target_child_tile = create_tile_on_concept(
            target_parent_tile.resourceinstance_id,
            source_child_tile.nodegroup_id,
            copy.deepcopy(source_child_tile.data),
            target_parent_tile.tileid,
            edit_transaction_id,
        )
        copied_tiles.append(target_child_tile)
        copied_tiles.extend(
            copy_child_tiles(
                source_child_tile,
                target_child_tile,
                source_child_tiles_by_parent_id,
                edit_transaction_id,
            )
        )
    return copied_tiles


def copy_tiles_to_survivor(
    survivor,
    absorbed,
    selected_tile_ids,
    pref_label_demotion_tile_ids,
    edit_transaction_id,
):
    """Copy the selected absorbed tiles onto the survivor, skipping duplicates.

    Cardinality-n tiles are appended; cardinality-1 tiles overwrite the
    survivor's existing tile. Child tiles follow their parent automatically,
    whether or not the editor selected them.
    """
    nodegroups_by_id = get_concept_nodegroups_by_id()
    alt_label_tile_value = get_list_item_tile_value(ALT_LABEL_LIST_ITEM_ID)

    source_tiles_by_id = {}
    source_child_tiles_by_parent_id = defaultdict(list)
    for source_tile in TileModel.objects.filter(resourceinstance_id=absorbed.pk):
        source_tiles_by_id[str(source_tile.tileid)] = source_tile
        if source_tile.parenttile_id:
            source_child_tiles_by_parent_id[str(source_tile.parenttile_id)].append(
                source_tile
            )

    survivor_identity_keys = {
        build_tile_identity_key(tile.nodegroup_id, tile.data)
        for tile in TileModel.objects.filter(resourceinstance_id=survivor.pk)
    }
    survivor_identity_keys.discard(None)

    copied_tiles = []
    for selected_tile_id in selected_tile_ids:
        source_tile = source_tiles_by_id[str(selected_tile_id)]
        nodegroup = nodegroups_by_id[str(source_tile.nodegroup_id)]

        tile_data = build_copied_tile_data(
            source_tile,
            str(selected_tile_id) in pref_label_demotion_tile_ids,
            alt_label_tile_value,
        )
        identity_key = build_tile_identity_key(source_tile.nodegroup_id, tile_data)
        if identity_key is not None and identity_key in survivor_identity_keys:
            continue

        if nodegroup.cardinality == SINGLE_CARDINALITY:
            target_tile = overwrite_single_cardinality_tile(
                survivor.pk,
                source_tile.nodegroup_id,
                tile_data,
                edit_transaction_id,
            )
        else:
            target_tile = create_tile_on_concept(
                survivor.pk,
                source_tile.nodegroup_id,
                tile_data,
                None,
                edit_transaction_id,
            )

        if identity_key is not None:
            survivor_identity_keys.add(identity_key)

        copied_tiles.append(target_tile)
        copied_tiles.extend(
            copy_child_tiles(
                source_tile,
                target_tile,
                source_child_tiles_by_parent_id,
                edit_transaction_id,
            )
        )

    return copied_tiles


def write_reciprocal_exact_match_tiles(survivor, absorbed, edit_transaction_id):
    """Record a skos:exactMatch on each concept pointing at the other's URI.

    The absorbed concept keeps its own URI and stays dereferenceable once
    retired, so without this the two records have no machine-readable link.
    Concepts without a URI tile are skipped rather than treated as an error.
    """
    survivor_uri = get_concept_uri(survivor.pk)
    absorbed_uri = get_concept_uri(absorbed.pk)
    if not survivor_uri or not absorbed_uri:
        return []

    exact_match_tile_value = get_list_item_tile_value(EXACT_MATCH_LIST_ITEM_ID)

    written_tiles = []
    for concept_id, matched_uri in (
        (survivor.pk, absorbed_uri),
        (absorbed.pk, survivor_uri),
    ):
        tile_data = {
            MATCH_STATUS_RELATION_NODE: [exact_match_tile_value],
            MATCH_STATUS_COMPARATE_NODE: matched_uri,
        }
        identity_key = build_tile_identity_key(MATCH_STATUS_NODEGROUP, tile_data)
        existing_identity_keys = {
            build_tile_identity_key(MATCH_STATUS_NODEGROUP, tile.data)
            for tile in TileModel.objects.filter(
                resourceinstance_id=concept_id,
                nodegroup_id=MATCH_STATUS_NODEGROUP,
            )
        }
        if identity_key in existing_identity_keys:
            continue

        written_tiles.append(
            create_tile_on_concept(
                concept_id,
                MATCH_STATUS_NODEGROUP,
                tile_data,
                None,
                edit_transaction_id,
            )
        )

    return written_tiles


def validate_merge(survivor, absorbed, selected_tile_ids, user_is_lingo_admin):
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
    if not survivor_scheme_id or survivor_scheme_id != absorbed_scheme_id:
        raise ConceptMergeError(
            _("Cannot merge"),
            _("Concepts can only be merged within the same scheme."),
        )

    if is_scheme_locked(survivor_scheme_id) and not user_is_lingo_admin:
        raise ConceptMergeError(
            _("Scheme is locked."),
            _("This concept's scheme is locked and cannot be edited."),
            status=HTTPStatus.LOCKED,
        )

    if not survivor.resource_instance_lifecycle_state.can_edit_resource_instances:
        raise ConceptMergeError(
            _("Cannot merge"),
            _("The surviving concept is in a state that cannot be edited."),
            status=HTTPStatus.CONFLICT,
        )

    if absorbed.resource_instance_lifecycle_state_id != EDITING_STATE_ID:
        raise ConceptMergeError(
            _("Cannot merge"),
            _(
                "Only a concept in the Editing state can be merged into another "
                "concept, because it must be retirable afterwards."
            ),
            status=HTTPStatus.CONFLICT,
        )

    validate_selected_tiles(absorbed, selected_tile_ids)


def validate_selected_tiles(absorbed, selected_tile_ids):
    nodegroups_by_id = get_concept_nodegroups_by_id()
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

        nodegroup = nodegroups_by_id[str(source_tile.nodegroup_id)]
        if nodegroup.grouping_node.alias in EXCLUDED_NODEGROUP_ALIASES:
            raise ConceptMergeError(
                _("Cannot merge"),
                _("%(alias)s values cannot be copied between concepts.")
                % {"alias": nodegroup.grouping_node.alias},
            )


def merge_concepts(survivor, absorbed, selections, user):
    """Apply a validated merge and return its audit record."""
    edit_transaction_id = uuid.uuid4()
    selected_tile_ids = selections.get("tile_selections") or []
    pref_label_demotion_tile_ids = {
        str(tile_id) for tile_id in selections.get("pref_label_demotions") or []
    }

    with transaction.atomic():
        copy_tiles_to_survivor(
            survivor,
            absorbed,
            selected_tile_ids,
            pref_label_demotion_tile_ids,
            edit_transaction_id,
        )

        if selections.get("create_exact_match_tiles", True):
            write_reciprocal_exact_match_tiles(survivor, absorbed, edit_transaction_id)

        return ConceptMerge.objects.create(
            survivor_concept_id=survivor.pk,
            absorbed_concept_id=absorbed.pk,
            user=user if user is not None and user.is_authenticated else None,
            edit_transaction_id=edit_transaction_id,
            selections=selections,
        )
