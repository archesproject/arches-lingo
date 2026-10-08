"""Tile writes a merge makes on the surviving concept, and on the absorbed one."""

import copy
from collections import defaultdict

from arches.app.models.models import TileModel
from arches.app.models.resource import Resource
from arches.app.models.tile import Tile

from arches_controlled_lists.models import ListItem

from arches_lingo.const import (
    ALT_LABEL_LIST_ITEM_ID,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_TYPE_NODE,
    DEPICTING_DIGITAL_ASSET_INTERNAL_NODE,
    DEPICTING_DIGITAL_ASSET_INTERNAL_NODEGROUP,
    EXACT_MATCH_LIST_ITEM_ID,
    MATCH_STATUS_COMPARATE_NODE,
    MATCH_STATUS_NODEGROUP,
    MATCH_STATUS_RELATION_NODE,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)
from arches_lingo.utils.concept_lifecycle import get_all_descendant_ids
from arches_lingo.utils.concept_merge.rules import ConceptMergeGraph

SINGLE_CARDINALITY = "1"

TILE_SELECTABLE = "selectable"
TILE_ALREADY_ON_SURVIVOR = "already_on_survivor"
TILE_DROPPED = "dropped"


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


def get_concept_uri(concept_id):
    uri_tile = TileModel.objects.filter(
        resourceinstance_id=concept_id,
        nodegroup_id=URI_NODEGROUP,
    ).first()
    return uri_tile.data.get(URI_CONTENT_NODE) if uri_tile else None


def get_list_item_tile_value(list_item_id):
    return ListItem.objects.get(pk=list_item_id).build_tile_value()


def get_survivor_descendant_ids_if_needed(merge_graph, survivor_id, absorbed_tiles):
    if not merge_graph.needs_survivor_descendants(absorbed_tiles):
        return set()
    return get_all_descendant_ids(str(survivor_id))


def prepare_tile_for_survivor(
    merge_graph,
    source_tile,
    survivor_id,
    survivor_descendant_ids,
    survivor_identity_keys,
    alt_label_tile_value=None,
):
    """Return (state, tile data, identity key) for carrying one tile across.

    The preview and the merge itself both go through here, so what the editor
    is shown as already present, or as dropped, is exactly what the merge does.
    Passing `alt_label_tile_value` demotes a preferred label on the way across.
    """
    tile_data = copy.deepcopy(source_tile.data)
    if alt_label_tile_value is not None:
        tile_data[CONCEPT_NAME_TYPE_NODE] = [alt_label_tile_value]

    tile_data = merge_graph.strip_self_references(
        source_tile.nodegroup_id, tile_data, survivor_id, survivor_descendant_ids
    )
    if tile_data is None:
        return TILE_DROPPED, None, None

    identity_key = merge_graph.build_tile_identity_key(
        source_tile.nodegroup_id, tile_data
    )
    if identity_key in survivor_identity_keys:
        return TILE_ALREADY_ON_SURVIVOR, tile_data, identity_key

    return TILE_SELECTABLE, tile_data, identity_key


def create_tile_on_concept(
    concept_id, nodegroup_id, tile_data, parent_tile_id, edit_transaction_id, resource
):
    """Save a tile through the Tile proxy so datatypes and graph functions run.

    Tiles are saved without a user because Tile.save() diverts data into
    provisional edits for any user who is not a resource reviewer, which would
    leave the merged values invisible. The merging user is recorded on the
    ConceptMerge instead, and edit log rows are grouped by transaction id.

    Indexing is off here; the merge indexes everything it touched in one pass
    once it commits.
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
    merge_graph = ConceptMergeGraph()
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

    selected_source_tiles = [
        source_tiles_by_id[str(selected_tile_id)]
        for selected_tile_id in selected_tile_ids
    ]
    survivor_identity_keys = merge_graph.collect_identity_keys(
        TileModel.objects.filter(resourceinstance_id=survivor.pk)
    )
    survivor_descendant_ids = get_survivor_descendant_ids_if_needed(
        merge_graph, survivor.pk, selected_source_tiles
    )

    copied_tiles = []
    for source_tile in selected_source_tiles:
        should_demote_pref_label = (
            str(source_tile.tileid) in pref_label_demotion_tile_ids
        )
        tile_state, tile_data, identity_key = prepare_tile_for_survivor(
            merge_graph,
            source_tile,
            survivor.pk,
            survivor_descendant_ids,
            survivor_identity_keys,
            alt_label_tile_value if should_demote_pref_label else None,
        )
        if tile_state != TILE_SELECTABLE:
            continue

        nodegroup = merge_graph.nodegroups_by_id[str(source_tile.nodegroup_id)]
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
    survivor_references = get_depicted_digital_object_references(survivor.pk)
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


def write_match_tiles(
    first_concept,
    second_concept,
    edit_transaction_id,
    relation_list_item_id=EXACT_MATCH_LIST_ITEM_ID,
    write_to_first=True,
    write_to_second=True,
):
    """Record a match relation (exactMatch by default) on each concept pointing
    at the other's URI. Only symmetric relations make sense here: the same
    relation is written in both directions.

    Concepts without a URI tile are skipped. `write_to_first` / `write_to_second`
    hold back a side the caller may not edit, such as a published concept.
    """
    first_uri = get_concept_uri(first_concept.pk)
    second_uri = get_concept_uri(second_concept.pk)
    if not first_uri or not second_uri:
        return []

    merge_graph = ConceptMergeGraph()
    relation_tile_value = get_list_item_tile_value(relation_list_item_id)
    resources_by_concept_id = load_concept_resources(
        first_concept.pk, second_concept.pk
    )

    matches_to_write = []
    if write_to_first:
        matches_to_write.append((first_concept.pk, second_uri))
    if write_to_second:
        matches_to_write.append((second_concept.pk, first_uri))

    written_tiles = []
    for concept_id, matched_uri in matches_to_write:
        tile_data = {
            MATCH_STATUS_RELATION_NODE: [relation_tile_value],
            MATCH_STATUS_COMPARATE_NODE: matched_uri,
        }
        existing_identity_keys = merge_graph.collect_identity_keys(
            TileModel.objects.filter(
                resourceinstance_id=concept_id,
                nodegroup_id=MATCH_STATUS_NODEGROUP,
            )
        )
        identity_key = merge_graph.build_tile_identity_key(
            MATCH_STATUS_NODEGROUP, tile_data
        )
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
