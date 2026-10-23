"""Which Concept nodegroups a merge may carry across, and how each one behaves.

Every rule is keyed by nodegroup alias and names nodes by alias, so nothing here
depends on node UUIDs. ConceptMergeGraph resolves the aliases against the Concept
graph once per operation.
"""

import json
from dataclasses import dataclass

from arches.app.models.models import Node, NodeGroup

from arches_lingo.const import CONCEPTS_GRAPH_ID


@dataclass(frozen=True)
class MergeSectionRule:
    # Nodes whose values decide when two tiles hold the same value. Left empty,
    # every node on the tile counts.
    identity_node_aliases: tuple[str, ...] = ()
    # Resource-instance nodes that can name the survivor itself, such as the
    # absorbed concept's broader tile when it is a child of the survivor.
    self_reference_node_aliases: tuple[str, ...] = ()
    # Also strip references to the survivor's descendants, so a copied broader
    # tile cannot make the survivor its own ancestor.
    strips_survivor_descendants: bool = False
    # Holds a reference that only resolves inside one scheme, so it is never
    # carried between concepts in different schemes.
    is_scheme_scoped: bool = False
    # A list of references kept on one tile and merged one reference at a time,
    # since copying the tile would replace the survivor's list instead of adding to it.
    is_reference_list: bool = False


# uri, identifier, part_of_scheme and data_assignment have no rule, so they are
# never carried across: a shared uri breaks URI resolution, identifiers are
# allocated per scheme, part_of_scheme would move the survivor, and
# data_assignment records who asserted the absorbed concept's values.
MERGE_SECTION_RULES = {
    "appellative_status": MergeSectionRule(
        identity_node_aliases=(
            "appellative_status_ascribed_name_content",
            "appellative_status_ascribed_name_language",
            "appellative_status_ascribed_relation",
        ),
    ),
    "statement": MergeSectionRule(
        identity_node_aliases=(
            "statement_content",
            "statement_language",
            "statement_type",
        ),
    ),
    "classification_status": MergeSectionRule(
        identity_node_aliases=("classification_status_ascribed_classification",),
        self_reference_node_aliases=("classification_status_ascribed_classification",),
        strips_survivor_descendants=True,
        is_scheme_scoped=True,
    ),
    "top_concept_of": MergeSectionRule(is_scheme_scoped=True),
    "relation_status": MergeSectionRule(
        identity_node_aliases=(
            "relation_status_ascribed_comparate",
            "relation_status_ascribed_relation",
        ),
        self_reference_node_aliases=("relation_status_ascribed_comparate",),
        is_scheme_scoped=True,
    ),
    "match_status": MergeSectionRule(
        identity_node_aliases=(
            "match_status_ascribed_comparate",
            "match_status_ascribed_relation",
        ),
    ),
    "type": MergeSectionRule(),
    "depicting_digital_asset_internal": MergeSectionRule(is_reference_list=True),
    "depicting_digital_asset_external": MergeSectionRule(),
    "also_instance_of": MergeSectionRule(),
    "status": MergeSectionRule(),
    "creation": MergeSectionRule(),
}


def normalize_reference_entry(entry):
    if isinstance(entry, dict):
        return entry.get("resourceId") or entry.get("uri")
    return entry


def normalize_node_value(node_value):
    """Reduce a node value to something hashable and comparable across tiles.

    Resource-instance and reference values carry per-tile bookkeeping alongside
    the value itself, so only the identifying part of each entry is kept.
    """
    if isinstance(node_value, list):
        return tuple(normalize_reference_entry(entry) for entry in node_value)
    if isinstance(node_value, dict):
        return json.dumps(node_value, sort_keys=True)
    return node_value


class ConceptMergeGraph:
    """The Concept graph's nodegroups and nodes, resolved once per merge."""

    def __init__(self):
        self.nodegroups_by_id = {
            str(nodegroup.pk): nodegroup
            for nodegroup in NodeGroup.objects.filter(
                grouping_node__graph_id=CONCEPTS_GRAPH_ID
            ).select_related("grouping_node")
        }
        self.node_ids_by_alias = {}
        self.data_node_ids_by_nodegroup_id = {}
        for node in Node.objects.filter(graph_id=CONCEPTS_GRAPH_ID).exclude(
            datatype="semantic"
        ):
            self.node_ids_by_alias[node.alias] = str(node.pk)
            self.data_node_ids_by_nodegroup_id.setdefault(
                str(node.nodegroup_id), []
            ).append(str(node.pk))

    def get_nodegroup_alias(self, nodegroup_id):
        return self.nodegroups_by_id[str(nodegroup_id)].grouping_node.alias

    def get_rule(self, nodegroup_id):
        return MERGE_SECTION_RULES.get(self.get_nodegroup_alias(nodegroup_id))

    def get_node_ids(self, node_aliases):
        return [self.node_ids_by_alias[node_alias] for node_alias in node_aliases]

    def build_tile_identity_key(self, nodegroup_id, tile_data):
        rule = self.get_rule(nodegroup_id)
        if rule is None:
            return None

        if rule.identity_node_aliases:
            identity_node_ids = self.get_node_ids(rule.identity_node_aliases)
        else:
            identity_node_ids = sorted(
                self.data_node_ids_by_nodegroup_id.get(str(nodegroup_id), [])
            )

        return (str(nodegroup_id),) + tuple(
            normalize_node_value(tile_data.get(node_id))
            for node_id in identity_node_ids
        )

    def collect_identity_keys(self, tiles):
        identity_keys = {
            self.build_tile_identity_key(tile.nodegroup_id, tile.data) for tile in tiles
        }
        identity_keys.discard(None)
        return identity_keys

    def strip_self_references(
        self, nodegroup_id, tile_data, survivor_id, survivor_descendant_ids=frozenset()
    ):
        """Drop references to the survivor from a tile copied off the absorbed concept.

        Returns None when a reference node is left empty, because a tile whose only
        content was the relationship between the two concepts has nothing left to
        say once the merge dissolves that relationship.
        """
        rule = self.get_rule(nodegroup_id)
        if rule is None or not rule.self_reference_node_aliases:
            return tile_data

        concept_ids_to_strip = {str(survivor_id)}
        if rule.strips_survivor_descendants:
            concept_ids_to_strip |= set(survivor_descendant_ids)

        stripped_tile_data = dict(tile_data)
        for node_id in self.get_node_ids(rule.self_reference_node_aliases):
            node_value = stripped_tile_data.get(node_id)
            if not isinstance(node_value, list):
                continue

            remaining_references = [
                entry
                for entry in node_value
                if not (
                    isinstance(entry, dict)
                    and str(entry.get("resourceId")) in concept_ids_to_strip
                )
            ]
            if not remaining_references:
                return None
            stripped_tile_data[node_id] = remaining_references

        return stripped_tile_data

    def needs_survivor_descendants(self, tiles):
        for tile in tiles:
            rule = self.get_rule(tile.nodegroup_id)
            if rule is not None and rule.strips_survivor_descendants:
                return True
        return False
