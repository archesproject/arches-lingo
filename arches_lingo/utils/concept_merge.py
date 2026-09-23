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
from django.db.models import Q
from django.utils.translation import gettext as _

from arches.app.models.models import NodeGroup, TileModel
from arches.app.models.resource import Resource
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
    DEPICTING_DIGITAL_ASSET_INTERNAL_NODE,
    DEPICTING_DIGITAL_ASSET_INTERNAL_NODEGROUP,
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
from arches_lingo.utils.concept_builder import ConceptBuilder
from arches_lingo.utils.concept_lifecycle import (
    EDITING_STATE_ID,
    STRATEGY_REPARENT_TO_SURVIVOR,
    VALID_STRATEGIES,
    get_narrower_ids,
    get_scheme_id_if_top_concept,
    index_concepts_in_transaction,
    retire_concept,
)
from arches_lingo.utils.scheme_lock import get_scheme_id_for_concept, is_scheme_locked

SINGLE_CARDINALITY = "1"

# Retiring the absorbed concept is part of the merge, so reparent_to_survivor is
# offered alongside the strategies the standalone retire endpoint accepts.
VALID_MERGE_RETIREMENT_STRATEGIES = VALID_STRATEGIES | {STRATEGY_REPARENT_TO_SURVIVOR}

# Nodegroups an editor may never pull across from the absorbed concept. This must
# stay in step with MERGE_SECTIONS on the client, which offers everything else.
# uri is cardinality-1 and ConceptURILookupView resolves by exact tile match, so
# two concepts must never carry the same one. identifier is allocated per scheme
# by ConceptIdentifierCounter and would misrepresent the survivor. part_of_scheme
# is always identical, since merges are restricted to a single scheme.
# data_assignment records who asserted the absorbed concept's values and when,
# which does not transfer to the survivor any more than an identifier does.
EXCLUDED_NODEGROUP_ALIASES = frozenset(
    {"uri", "identifier", "part_of_scheme", "data_assignment"}
)

# Nodegroups whose values only mean anything inside one scheme, so they are never
# copied between concepts in different schemes. Each holds a resource-instance
# reference: classification_status and relation_status point at Concepts, and
# top_concept_of points at the Scheme itself. Carrying any of them across would
# leave the survivor placed in, or related to, a vocabulary it is not part of.
# This must stay in step with the client's schemeScoped sections.
SCHEME_SCOPED_NODEGROUP_ALIASES = frozenset(
    {"classification_status", "top_concept_of", "relation_status"}
)

# Nodegroups holding a list of references on a single tile, merged one reference
# at a time rather than as a whole tile. A concept keeps all of its images on one
# depicting_digital_asset_internal tile, so copying that tile would replace the
# survivor's images instead of adding to them.
REFERENCE_LIST_NODEGROUP_IDS = frozenset({DEPICTING_DIGITAL_ASSET_INTERNAL_NODEGROUP})

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

# Resource-instance nodes on a copied tile that may name the survivor itself:
# the absorbed concept's broader tile when it is a child of the survivor, or a
# relation recorded between the two. Copied verbatim these leave the survivor
# pointing at itself, so the reference is dropped on the way across.
SELF_REFERENCE_NODES_BY_NODEGROUP = {
    CLASSIFICATION_STATUS_NODEGROUP: (
        CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    ),
    RELATION_STATUS_NODEGROUP: (RELATION_STATUS_ASCRIBED_COMPARATE_NODEID,),
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


def load_concept_resources(*concept_ids):
    """Return {concept id: Resource} with the graph publication already joined.

    Tile.save() otherwise fetches the resource and its serialized graph for
    every tile it writes, which for a merge is the same two concepts over and
    over.
    """
    resources = Resource.objects.select_related("graph__publication").filter(
        pk__in=[str(concept_id) for concept_id in concept_ids]
    )
    return {str(resource.pk): resource for resource in resources}


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


def strip_self_references(nodegroup_id, tile_data, survivor_id):
    """Drop references to the survivor from a tile copied off the absorbed concept.

    Returns None when a reference node is left empty, because a tile whose only
    content was the relationship between the two concepts has nothing left to say
    once that relationship has been dissolved by the merge.
    """
    reference_node_ids = SELF_REFERENCE_NODES_BY_NODEGROUP.get(str(nodegroup_id))
    if not reference_node_ids:
        return tile_data

    stripped_tile_data = dict(tile_data)
    for node_id in reference_node_ids:
        node_value = stripped_tile_data.get(node_id)
        if not isinstance(node_value, list):
            continue

        remaining_references = [
            entry
            for entry in node_value
            if not (
                isinstance(entry, dict)
                and str(entry.get("resourceId")) == str(survivor_id)
            )
        ]
        if not remaining_references:
            return None
        stripped_tile_data[node_id] = remaining_references

    return stripped_tile_data


def create_tile_on_concept(
    concept_id, nodegroup_id, tile_data, parent_tile_id, edit_transaction_id, resource
):
    """Save a tile through the Tile proxy so datatypes and graph functions run.

    Tiles are saved without a user because Tile.save() diverts data into
    provisional edits for any user who is not a resource reviewer, which would
    leave the merged values invisible. The merging user is recorded on the
    ConceptMerge instead, and edit log rows are grouped by transaction id.

    `resource` is the concept the tile belongs to, handed in so the whole merge
    shares one instance rather than refetching it -- and its graph publication
    -- on every save. Indexing is off for the same reason; see
    `index_concepts_in_transaction`.
    """
    tile = Tile(
        resourceinstance_id=concept_id,
        nodegroup_id=nodegroup_id,
        parenttile_id=parent_tile_id,
        data=tile_data,
    )
    tile.save(
        request=None,
        transaction_id=edit_transaction_id,
        resource=resource,
        index=False,
    )
    return tile


def overwrite_single_cardinality_tile(
    concept_id, nodegroup_id, tile_data, edit_transaction_id, resource
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
            concept_id, nodegroup_id, tile_data, None, edit_transaction_id, resource
        )

    for child_tile in Tile.objects.filter(parenttile_id=existing_tile.tileid):
        child_tile.delete(request=None, index=False)

    tile = Tile.objects.get(tileid=existing_tile.tileid)
    tile.data = tile_data
    tile.save(
        request=None,
        transaction_id=edit_transaction_id,
        resource=resource,
        index=False,
    )
    return tile


def copy_child_tiles(
    source_parent_tile,
    target_parent_tile,
    source_child_tiles_by_parent_id,
    edit_transaction_id,
    resource,
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
            resource,
        )
        copied_tiles.append(target_child_tile)
        copied_tiles.extend(
            copy_child_tiles(
                source_child_tile,
                target_child_tile,
                source_child_tiles_by_parent_id,
                edit_transaction_id,
                resource,
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
    survivor_resource = load_concept_resources(survivor.pk)[str(survivor.pk)]

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
        tile_data = strip_self_references(
            source_tile.nodegroup_id, tile_data, survivor.pk
        )
        if tile_data is None:
            continue

        identity_key = build_tile_identity_key(source_tile.nodegroup_id, tile_data)
        if identity_key is not None and identity_key in survivor_identity_keys:
            continue

        if nodegroup.cardinality == SINGLE_CARDINALITY:
            target_tile = overwrite_single_cardinality_tile(
                survivor.pk,
                source_tile.nodegroup_id,
                tile_data,
                edit_transaction_id,
                survivor_resource,
            )
        else:
            target_tile = create_tile_on_concept(
                survivor.pk,
                source_tile.nodegroup_id,
                tile_data,
                None,
                edit_transaction_id,
                survivor_resource,
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
                survivor_resource,
            )
        )

    return copied_tiles


def get_depicted_digital_object_references(concept_id):
    image_tile = TileModel.objects.filter(
        resourceinstance_id=concept_id,
        nodegroup_id=DEPICTING_DIGITAL_ASSET_INTERNAL_NODEGROUP,
    ).first()
    if image_tile is None:
        return []
    return image_tile.data.get(DEPICTING_DIGITAL_ASSET_INTERNAL_NODE) or []


def append_digital_objects_to_survivor(
    survivor, absorbed, selected_digital_object_ids, edit_transaction_id
):
    """Add the selected absorbed images to the survivor's own list of images.

    References the survivor already holds are skipped. Each copied reference is
    saved afresh, so the datatype issues it a new resourceXresourceId and
    records the survivor's own relationship to the digital object.
    """
    selected_digital_object_ids = {
        str(digital_object_id) for digital_object_id in selected_digital_object_ids
    }
    if not selected_digital_object_ids:
        return None

    survivor_image_tile = Tile.objects.filter(
        resourceinstance_id=survivor.pk,
        nodegroup_id=DEPICTING_DIGITAL_ASSET_INTERNAL_NODEGROUP,
    ).first()
    survivor_references = (
        survivor_image_tile.data.get(DEPICTING_DIGITAL_ASSET_INTERNAL_NODE) or []
        if survivor_image_tile
        else []
    )
    survivor_digital_object_ids = {
        str(reference.get("resourceId")) for reference in survivor_references
    }

    references_to_add = [
        copy.deepcopy(reference)
        for reference in get_depicted_digital_object_references(absorbed.pk)
        if str(reference.get("resourceId")) in selected_digital_object_ids
        and str(reference.get("resourceId")) not in survivor_digital_object_ids
    ]
    if not references_to_add:
        return None

    survivor_resource = load_concept_resources(survivor.pk)[str(survivor.pk)]
    if survivor_image_tile is None:
        return create_tile_on_concept(
            survivor.pk,
            DEPICTING_DIGITAL_ASSET_INTERNAL_NODEGROUP,
            {DEPICTING_DIGITAL_ASSET_INTERNAL_NODE: references_to_add},
            None,
            edit_transaction_id,
            survivor_resource,
        )

    survivor_image_tile.data = {
        **survivor_image_tile.data,
        DEPICTING_DIGITAL_ASSET_INTERNAL_NODE: survivor_references + references_to_add,
    }
    survivor_image_tile.save(
        request=None,
        transaction_id=edit_transaction_id,
        resource=survivor_resource,
        index=False,
    )
    return survivor_image_tile


def demote_pref_label_tiles(tile_ids, edit_transaction_id):
    """Retype existing appellative_status tiles from prefLabel to altLabel.

    Needed when the editor picks the absorbed concept's preferred label for a
    language: the survivor's own preferred label in that language has to step
    down so that one preferred label per language still holds.
    """
    if not tile_ids:
        return []

    alt_label_tile_value = get_list_item_tile_value(ALT_LABEL_LIST_ITEM_ID)

    tiles_to_demote = list(
        Tile.objects.filter(tileid__in=tile_ids, nodegroup_id=CONCEPT_NAME_NODEGROUP)
    )
    resources_by_concept_id = load_concept_resources(
        *{tile.resourceinstance_id for tile in tiles_to_demote}
    )

    demoted_tiles = []
    for tile in tiles_to_demote:
        tile.data = {**tile.data, CONCEPT_NAME_TYPE_NODE: [alt_label_tile_value]}
        tile.save(
            request=None,
            transaction_id=edit_transaction_id,
            resource=resources_by_concept_id[str(tile.resourceinstance_id)],
            index=False,
        )
        demoted_tiles.append(tile)

    return demoted_tiles


def write_reciprocal_exact_match_tiles(
    survivor, absorbed, edit_transaction_id, write_to_absorbed=True
):
    """Record a skos:exactMatch on each concept pointing at the other's URI.

    The absorbed concept keeps its own URI and stays dereferenceable once
    retired, so without this the two records have no machine-readable link.
    Concepts without a URI tile are skipped rather than treated as an error.

    `write_to_absorbed` false records the match on the survivor alone, for an
    absorbed concept the merge is not allowed to edit -- a published or locked
    concept in another scheme. The half that can be written is the half that
    matters, since it is the survivor an editor will be reading from.
    """
    survivor_uri = get_concept_uri(survivor.pk)
    absorbed_uri = get_concept_uri(absorbed.pk)
    if not survivor_uri or not absorbed_uri:
        return []

    exact_match_tile_value = get_list_item_tile_value(EXACT_MATCH_LIST_ITEM_ID)
    resources_by_concept_id = load_concept_resources(survivor.pk, absorbed.pk)

    matches_to_write = [(survivor.pk, absorbed_uri)]
    if write_to_absorbed:
        matches_to_write.append((absorbed.pk, survivor_uri))

    written_tiles = []
    for concept_id, matched_uri in matches_to_write:
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
                resources_by_concept_id[str(concept_id)],
            )
        )

    return written_tiles


def get_concept_merge_history(concept_id):
    """Summarise every merge this concept took part in, newest first.

    Direction is expressed from this concept's point of view: "absorbed" means it
    took another concept's values in, "merged_into" means it was the one folded
    away and its URI now points at the counterpart.
    """
    merges = list(
        ConceptMerge.objects.filter(
            Q(survivor_concept_id=concept_id) | Q(absorbed_concept_id=concept_id)
        )
    )
    if not merges:
        return []

    counterpart_ids = [
        str(
            merge.absorbed_concept_id
            if str(merge.survivor_concept_id) == str(concept_id)
            else merge.survivor_concept_id
        )
        for merge in merges
    ]

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
                "counterpart_concept_id": counterpart_id,
                "counterpart_concept_labels": labels_by_concept_id.get(
                    counterpart_id, []
                ),
            }
        )
    return history


def concept_is_writable(concept, user_is_lingo_admin):
    """Whether the merge may add tiles to this concept.

    A concept the merge only reads from needs no such permission, which is what
    lets a published or locked concept in another scheme be absorbed.
    """
    if not concept.resource_instance_lifecycle_state.can_edit_resource_instances:
        return False

    scheme_id = resolve_scheme_id(concept.pk)
    if scheme_id and is_scheme_locked(scheme_id) and not user_is_lingo_admin:
        return False

    return True


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

    if not survivor.resource_instance_lifecycle_state.can_edit_resource_instances:
        raise ConceptMergeError(
            _("Cannot merge"),
            _("The surviving concept is in a state that cannot be edited."),
            status=HTTPStatus.CONFLICT,
        )

    # Within a scheme the absorbed concept is retired as part of the merge, which
    # only the Editing state allows. Across schemes it is never retired, so it is
    # read from and nothing about its state stands in the way.
    if not is_cross_scheme and (
        absorbed.resource_instance_lifecycle_state_id != EDITING_STATE_ID
    ):
        raise ConceptMergeError(
            _("Cannot merge"),
            _(
                "Only a concept in the Editing state can be merged into another "
                "concept in the same scheme, because it must be retirable "
                "afterwards."
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
    validate_retirement(absorbed, selections, is_cross_scheme)


def validate_retirement(absorbed, selections, is_cross_scheme=False):
    if not selections.get("retire_absorbed_concept"):
        return

    # Retiring rehomes the concept's children, and every strategy for doing so
    # resolves within one scheme: they move to the surviving concept, to the
    # retiring concept's own parents, or to the top of its scheme.
    if is_cross_scheme:
        raise ConceptMergeError(
            _("Cannot merge"),
            _(
                "A concept can only be retired by a merge within its own "
                "scheme. Merging across schemes leaves it in place."
            ),
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
                "should be handled before retiring it."
            ),
        )


def validate_pref_label_demotions(concept, tile_ids, error_message):
    """Reject any demotion that does not name a label tile of the given concept.

    Both sides of a merge can have a preferred label stepped down, so the same
    check runs twice with the message that names the side it was called for.
    """
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

        if str(source_tile.nodegroup_id) in REFERENCE_LIST_NODEGROUP_IDS:
            raise ConceptMergeError(
                _("Cannot merge"),
                _(
                    "Images are merged one at a time. Select them with "
                    "digital_object_selections rather than by tile."
                ),
            )

        nodegroup = nodegroups_by_id[str(source_tile.nodegroup_id)]
        if nodegroup.grouping_node.alias in EXCLUDED_NODEGROUP_ALIASES:
            raise ConceptMergeError(
                _("Cannot merge"),
                _("%(alias)s values cannot be copied between concepts.")
                % {"alias": nodegroup.grouping_node.alias},
            )

        if (
            is_cross_scheme
            and nodegroup.grouping_node.alias in SCHEME_SCOPED_NODEGROUP_ALIASES
        ):
            raise ConceptMergeError(
                _("Cannot merge"),
                _(
                    "%(alias)s values belong to a single scheme and cannot be "
                    "copied between concepts in different schemes."
                )
                % {"alias": nodegroup.grouping_node.alias},
            )


def merge_concepts(survivor, absorbed, selections, user, user_is_lingo_admin=False):
    """Apply a validated merge and return its audit record."""
    edit_transaction_id = uuid.uuid4()
    selected_tile_ids = selections.get("tile_selections") or []
    pref_label_demotion_tile_ids = {
        str(tile_id) for tile_id in selections.get("pref_label_demotions") or []
    }
    survivor_pref_label_demotion_tile_ids = {
        str(tile_id)
        for tile_id in selections.get("survivor_pref_label_demotions") or []
    }

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

        # Retiring here rather than in a follow-up request means a failure anywhere
        # in the merge rolls the retirement back with it, so the two concepts are
        # never left half-merged.
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
            user=user if user is not None and user.is_authenticated else None,
            edit_transaction_id=edit_transaction_id,
            selections=selections,
        )

    # One bulk pass over everything the merge touched, rather than a round trip
    # per tile inside the loops above. Running it after the transaction commits
    # keeps a rolled-back merge out of the index, and means both concepts are
    # indexed as they finally stand rather than mid-merge.
    index_concepts_in_transaction(
        edit_transaction_id, additional_concept_ids=(survivor.pk, absorbed.pk)
    )
    return concept_merge
