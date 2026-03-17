"""Advanced search query evaluation engine for Arches Lingo.

Evaluates a composable boolean query tree of concept search facets,
returning matching concept resource instance IDs.
"""

from django.db.models import Q

from arches.app.models.models import ResourceInstance, TileModel

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_TYPE_NODE,
    CLASSIFICATION_STATUS_NODEGROUP,
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    RELATION_STATUS_NODEGROUP,
    RELATION_STATUS_ASCRIBED_COMPARATE_NODEID,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
    STATEMENT_NODEGROUP,
    STATEMENT_CONTENT_NODE,
    STATEMENT_LANGUAGE_NODE,
    STATEMENT_TYPE_NODE,
    URI_NODEGROUP,
    URI_CONTENT_NODE,
    IDENTIFIER_NODEGROUP,
    IDENTIFIER_CONTENT_NODE,
    MATCH_STATUS_NODEGROUP,
    MATCH_STATUS_COMPARATE_NODE,
    CONCEPT_TYPE_NODEGROUP,
    CONCEPT_TYPE_NODEID,
)
from arches_lingo.models import ConceptSet


VALID_FACETS = {
    "label",
    "note",
    "language",
    "concept_type",
    "relationship_hierarchical",
    "relationship_associated",
    "match_uri",
    "scheme",
    "uri",
    "identifier",
    "lifecycle_state",
    "concept_set",
}


class AdvancedSearchEvaluator:
    """Evaluates an advanced search query tree and returns concept IDs."""

    def __init__(self, user=None):
        self.user = user

    def evaluate(self, query_node):
        """Evaluate a query node (group or condition) and return concept IDs.

        Returns a QuerySet of resource instance PKs (UUIDs).
        """
        if "operator" in query_node:
            return self._evaluate_group(query_node)
        elif "facet" in query_node:
            return self._evaluate_condition(query_node)
        else:
            return self._all_concept_ids()

    def _all_concept_ids(self):
        return ResourceInstance.objects.filter(graph_id=CONCEPTS_GRAPH_ID).values_list(
            "pk", flat=True
        )

    def _empty_concept_ids(self):
        return ResourceInstance.objects.none().values_list("pk", flat=True)

    def _evaluate_group(self, group_node):
        """Evaluate a boolean group with AND/OR operator.

        Uses database-level UNION/INTERSECT rather than loading full result
        sets into Python memory.
        """
        operator = group_node.get("operator", "and").lower()
        conditions = group_node.get("conditions", [])

        if not conditions:
            return self._all_concept_ids()

        result_ids = None
        for condition in conditions:
            child_ids = self.evaluate(condition)
            if result_ids is None:
                result_ids = child_ids
            elif operator == "and":
                result_ids = result_ids.intersection(child_ids)
            else:  # "or"
                result_ids = result_ids.union(child_ids)

        return result_ids

    def _evaluate_condition(self, condition):
        """Evaluate a single facet condition and return concept IDs."""
        facet = condition.get("facet")

        if facet not in VALID_FACETS:
            return self._empty_concept_ids()

        handler = getattr(self, f"_facet_{facet}", None)
        if handler is None:
            return self._empty_concept_ids()

        result_ids = handler(condition)

        # Apply negation using database-level EXCEPT rather than Python set subtraction.
        if condition.get("negated"):
            return self._all_concept_ids().difference(result_ids)

        return result_ids

    def _concept_ids_from_tiles(self, nodegroup_id, extra_filters=None):
        """Get distinct concept resource IDs from tiles in a nodegroup."""
        qs = TileModel.objects.filter(nodegroup_id=nodegroup_id)
        if extra_filters:
            qs = qs.filter(extra_filters)
        return qs.values_list("resourceinstance_id", flat=True).distinct()

    MATCH_MODE_LOOKUPS = {
        "contains": "icontains",
        "exact": "iexact",
        "starts_with": "istartswith",
        "ends_with": "iendswith",
    }

    def _text_filter(self, field, value, match_mode="contains"):
        """Build a Q filter for a text field using the given match mode.

        ``match_mode`` of ``"exists"`` checks for non-empty/non-null values.
        """
        if match_mode == "exists":
            return ~Q(**{field: ""}) & ~Q(**{field: None})
        lookup = self.MATCH_MODE_LOOKUPS.get(match_mode, "icontains")
        return Q(**{f"{field}__{lookup}": value})

    def _facet_label(self, condition):
        """Search by label text, optionally filtered by type and language."""
        filters = Q(nodegroup_id=CONCEPT_NAME_NODEGROUP)

        value = condition.get("value", "").strip()
        match_mode = condition.get("match_mode", "contains")
        if match_mode == "exists" or value:
            filters &= self._text_filter(
                f"data__{CONCEPT_NAME_CONTENT_NODE}", value, match_mode
            )

        label_type = condition.get("label_type")
        if label_type:
            # Reference data: list_item_id is nested inside the labels array
            filters &= Q(
                **{
                    f"data__{CONCEPT_NAME_TYPE_NODE}__contains": [
                        {"labels": [{"list_item_id": label_type}]}
                    ]
                }
            )

        language = condition.get("language")
        if language:
            # Language datatype stores code string directly
            filters &= Q(**{f"data__{CONCEPT_NAME_LANGUAGE_NODE}": language})

        return (
            TileModel.objects.filter(filters)
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

    def _facet_note(self, condition):
        """Search by note (statement) text, optionally by type and language."""
        filters = Q(nodegroup_id=STATEMENT_NODEGROUP)

        value = condition.get("value", "").strip()
        match_mode = condition.get("match_mode", "contains")
        if match_mode == "exists" or value:
            filters &= self._text_filter(
                f"data__{STATEMENT_CONTENT_NODE}", value, match_mode
            )

        note_type = condition.get("note_type")
        if note_type:
            # Reference data: list_item_id is nested inside the labels array
            filters &= Q(
                **{
                    f"data__{STATEMENT_TYPE_NODE}__contains": [
                        {"labels": [{"list_item_id": note_type}]}
                    ]
                }
            )

        language = condition.get("language")
        if language:
            filters &= Q(**{f"data__{STATEMENT_LANGUAGE_NODE}": language})

        return (
            TileModel.objects.filter(filters)
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

    def _facet_language(self, condition):
        """Find concepts that have any label or note in a specific language."""
        language = condition.get("value")
        if not language:
            return self._all_concept_ids()

        label_concepts = (
            TileModel.objects.filter(
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                **{f"data__{CONCEPT_NAME_LANGUAGE_NODE}": language},
            )
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

        note_concepts = (
            TileModel.objects.filter(
                nodegroup_id=STATEMENT_NODEGROUP,
                **{f"data__{STATEMENT_LANGUAGE_NODE}": language},
            )
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

        return label_concepts.union(note_concepts)

    def _facet_concept_type(self, condition):
        """Filter by concept type (reference data list_item_id)."""
        type_id = condition.get("value")
        if not type_id:
            return self._all_concept_ids()

        return (
            TileModel.objects.filter(
                nodegroup_id=CONCEPT_TYPE_NODEGROUP,
                **{
                    f"data__{CONCEPT_TYPE_NODEID}__contains": [
                        {"labels": [{"list_item_id": type_id}]}
                    ]
                },
            )
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

    def _facet_relationship_hierarchical(self, condition):
        """Find concepts with a hierarchical relationship to a given concept.

        direction: "broader" (concept has the target as a broader concept)
                   "narrower" (concept has the target as a narrower concept)
        """
        target_id = condition.get("value")
        direction = condition.get("direction", "broader")

        if not target_id:
            return self._all_concept_ids()

        if direction == "broader":
            # Find concepts that have target_id as their broader concept
            return (
                TileModel.objects.filter(
                    nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
                    **{
                        f"data__{CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID}__contains": [
                            {"resourceId": target_id}
                        ]
                    },
                )
                .values_list("resourceinstance_id", flat=True)
                .distinct()
            )
        else:  # narrower
            # The broader-concept IDs are embedded in JSONB arrays, so we extract
            # them in Python (bounded to a single concept's tile data).
            narrower_tiles = TileModel.objects.filter(
                nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
                resourceinstance_id=target_id,
            )
            broader_ids = set()
            for tile in narrower_tiles:
                classifications = tile.data.get(
                    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID, []
                )
                if classifications:
                    for item in classifications:
                        resource_id = item.get("resourceId")
                        if resource_id:
                            broader_ids.add(resource_id)
            return ResourceInstance.objects.filter(pk__in=broader_ids).values_list(
                "pk", flat=True
            )

    def _facet_relationship_associated(self, condition):
        """Find concepts associated with a given concept."""
        target_id = condition.get("value")
        if not target_id:
            return self._all_concept_ids()

        # Concepts that have target_id in their relation_status
        forward = (
            TileModel.objects.filter(
                nodegroup_id=RELATION_STATUS_NODEGROUP,
                **{
                    f"data__{RELATION_STATUS_ASCRIBED_COMPARATE_NODEID}__contains": [
                        {"resourceId": target_id}
                    ]
                },
            )
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

        # The comparate IDs for the reverse direction are embedded in JSONB arrays,
        # so we extract them in Python (bounded to a single concept's tile data).
        reverse_tiles = TileModel.objects.filter(
            nodegroup_id=RELATION_STATUS_NODEGROUP,
            resourceinstance_id=target_id,
        )
        reverse_ids = set()
        for tile in reverse_tiles:
            comparates = tile.data.get(RELATION_STATUS_ASCRIBED_COMPARATE_NODEID, [])
            if comparates:
                for item in comparates:
                    resource_id = item.get("resourceId")
                    if resource_id:
                        reverse_ids.add(resource_id)

        reverse_qs = ResourceInstance.objects.filter(pk__in=reverse_ids).values_list(
            "pk", flat=True
        )
        return forward.union(reverse_qs)

    def _facet_match_uri(self, condition):
        """Find concepts with a matching URI in match_status."""
        value = condition.get("value", "").strip()
        match_mode = condition.get("match_mode", "contains")
        if not value and match_mode != "exists":
            return self._all_concept_ids()

        filters = Q(nodegroup_id=MATCH_STATUS_NODEGROUP)
        filters &= self._text_filter(
            f"data__{MATCH_STATUS_COMPARATE_NODE}", value, match_mode
        )

        return (
            TileModel.objects.filter(filters)
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

    def _facet_scheme(self, condition):
        """Find concepts that belong to a specific scheme."""
        scheme_id = condition.get("value")
        if not scheme_id:
            return self._all_concept_ids()

        # Direct scheme membership via part_of_scheme
        direct_members = (
            TileModel.objects.filter(
                nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
                **{
                    f"data__{CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}__contains": [
                        {"resourceId": scheme_id}
                    ]
                },
            )
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

        # Top concepts of the scheme
        top_concepts = (
            TileModel.objects.filter(
                nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
                **{
                    f"data__{TOP_CONCEPT_OF_NODE_AND_NODEGROUP}__contains": [
                        {"resourceId": scheme_id}
                    ]
                },
            )
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

        return direct_members.union(top_concepts)

    def _facet_uri(self, condition):
        """Search by concept URI."""
        value = condition.get("value", "").strip()
        match_mode = condition.get("match_mode", "contains")
        if not value and match_mode != "exists":
            return self._all_concept_ids()

        filters = Q(nodegroup_id=URI_NODEGROUP)
        if match_mode == "exists":
            filters &= ~Q(**{f"data__{URI_CONTENT_NODE}": None})
        else:
            lookup = self.MATCH_MODE_LOOKUPS.get(match_mode, "icontains")
            filters &= Q(**{f"data__{URI_CONTENT_NODE}__{lookup}": value})

        return (
            TileModel.objects.filter(filters)
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

    def _facet_identifier(self, condition):
        """Search by concept identifier."""
        value = condition.get("value", "").strip()
        match_mode = condition.get("match_mode", "contains")
        if not value and match_mode != "exists":
            return self._all_concept_ids()

        filters = Q(nodegroup_id=IDENTIFIER_NODEGROUP)
        filters &= self._text_filter(
            f"data__{IDENTIFIER_CONTENT_NODE}", value, match_mode
        )

        return (
            TileModel.objects.filter(filters)
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

    def _facet_lifecycle_state(self, condition):
        """Filter by resource instance lifecycle state."""
        value = condition.get("value")
        if not value:
            return self._all_concept_ids()

        return ResourceInstance.objects.filter(
            graph_id=CONCEPTS_GRAPH_ID,
            resource_instance_lifecycle_state_id=value,
        ).values_list("pk", flat=True)

    def _facet_concept_set(self, condition):
        """Return concepts from a saved concept set."""
        set_id = condition.get("value")
        if not set_id:
            return self._empty_concept_ids()

        try:
            concept_set = ConceptSet.objects.get(pk=set_id, user=self.user)
        except ConceptSet.DoesNotExist:
            return self._empty_concept_ids()

        return concept_set.members.values_list("concept_id", flat=True)
