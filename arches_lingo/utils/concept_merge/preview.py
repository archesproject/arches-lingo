from arches.app.models.models import TileModel

from arches_lingo.utils.concept_merge.rules import (
    MERGE_SECTION_RULES,
    ConceptMergeGraph,
)
from arches_lingo.utils.concept_merge.tiles import (
    get_survivor_descendant_ids_if_needed,
    prepare_tile_for_survivor,
)
from arches_lingo.utils.concept_merge.validation import resolve_scheme_id

TILE_BLOCKED = "blocked"


def get_absorbed_tiles_offered_by_tile(merge_graph, absorbed_id):
    offered_tiles = []
    for tile in TileModel.objects.filter(
        resourceinstance_id=absorbed_id, parenttile__isnull=True
    ):
        rule = merge_graph.get_rule(tile.nodegroup_id)
        if rule is not None and not rule.is_reference_list:
            offered_tiles.append(tile)
    return offered_tiles


def build_merge_preview(survivor, absorbed):
    """Describe what merging `absorbed` into `survivor` would do with each tile.

    Every absorbed tile an editor could pick is given a state -- selectable,
    already on the survivor, dropped because it only names the survivor, or
    blocked because it cannot leave its scheme -- worked out by the same code
    the merge runs, so the client never has to mirror those rules.
    """
    survivor_id = str(survivor.pk)
    absorbed_id = str(absorbed.pk)
    merge_graph = ConceptMergeGraph()
    is_cross_scheme = resolve_scheme_id(survivor_id) != resolve_scheme_id(absorbed_id)

    absorbed_tiles = get_absorbed_tiles_offered_by_tile(merge_graph, absorbed_id)
    survivor_identity_keys = merge_graph.collect_identity_keys(
        TileModel.objects.filter(resourceinstance_id=survivor_id)
    )
    survivor_descendant_ids = get_survivor_descendant_ids_if_needed(
        merge_graph, survivor_id, absorbed_tiles
    )

    tile_states = {}
    for tile in absorbed_tiles:
        if is_cross_scheme and merge_graph.get_rule(tile.nodegroup_id).is_scheme_scoped:
            tile_states[str(tile.tileid)] = TILE_BLOCKED
            continue
        tile_state, _tile_data, _identity_key = prepare_tile_for_survivor(
            merge_graph,
            tile,
            survivor_id,
            survivor_descendant_ids,
            survivor_identity_keys,
        )
        tile_states[str(tile.tileid)] = tile_state

    blocked_nodegroup_aliases = []
    if is_cross_scheme:
        blocked_nodegroup_aliases = [
            nodegroup_alias
            for nodegroup_alias, rule in MERGE_SECTION_RULES.items()
            if rule.is_scheme_scoped
        ]

    return {
        "is_cross_scheme": is_cross_scheme,
        "tile_states": tile_states,
        "blocked_nodegroup_aliases": blocked_nodegroup_aliases,
    }
