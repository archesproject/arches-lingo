"""Advanced search query evaluation engine for Arches Lingo.

Evaluates a composable boolean query tree of concept search facets,
returning matching concept resource instance IDs.

Performance notes
-----------------
Every facet handler returns a **QuerySet** (not a materialised Python list).
Boolean AND/OR combinations are composed using Django subquery expressions so
that the database performs all set operations rather than Python.  The final
result is paginated before any rows are fetched.

Cascade (full-hierarchy) traversal uses a PostgreSQL recursive CTE executed
in a single round-trip rather than a Python BFS loop that would require one
database query per level of the hierarchy.  The CTE results are materialised
as a list of UUIDs in Python before being passed back to a QuerySet filter so
that the rest of the AND/OR composition machinery can continue to use lazy
QuerySets.
"""

from django.db import connection
from django.db.models import Q
from django.db.models.expressions import RawSQL

from arches.app.models.models import ResourceInstance, TileModel

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_DATA_ASSIGNMENT_ACTOR_NODE,
    CONCEPT_NAME_DATA_ASSIGNMENT_OBJ_USED_NODE,
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
    STATEMENT_DATA_ASSIGNMENT_ACTOR_NODE,
    STATEMENT_DATA_ASSIGNMENT_OBJ_USED_NODE,
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
    "top_concept",
    "uri",
    "identifier",
    "lifecycle_state",
    "concept_set",
    "attribution_source",
    "attribution_contributor",
}


class AdvancedSearchEvaluator:
    """Evaluates an advanced search query tree and returns concept IDs.

    All facet handlers return a lazy QuerySet of resource-instance PKs so that
    boolean AND/OR composition and negation are expressed as database
    subqueries rather than Python set operations on materialised lists.
    """

    def __init__(self, user=None):
        self.user = user

    def evaluate(self, query_node):
        """Evaluate a query node (group or condition) and return a QuerySet of PKs."""
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

    def _evaluate_group(self, group_node):
        """Evaluate a boolean group with AND/OR operator using DB subqueries."""
        operator = group_node.get("operator", "and").lower()
        conditions = group_node.get("conditions", [])

        if not conditions:
            return self._all_concept_ids()

        result_qs = None
        for condition in conditions:
            child_qs = self.evaluate(condition)
            if result_qs is None:
                result_qs = child_qs
            elif operator == "and":
                # Intersect via two ResourceInstance subqueries.  Normalising to
                # ResourceInstance here is necessary because facet handlers may
                # return TileModel querysets (selecting resourceinstance_id) or
                # ResourceInstance querysets — mixing them with a plain
                # .filter(pk__in=child_qs) would filter by TileModel.pk (tileid)
                # instead of the FK value, always producing an empty result.
                result_qs = (
                    ResourceInstance.objects.filter(graph_id=CONCEPTS_GRAPH_ID)
                    .filter(pk__in=result_qs)
                    .filter(pk__in=child_qs)
                    .values_list("pk", flat=True)
                )
            else:  # "or"
                # Union: combine via Q(pk__in) | Q(pk__in) so the DB resolves it.
                result_qs = (
                    ResourceInstance.objects.filter(graph_id=CONCEPTS_GRAPH_ID)
                    .filter(Q(pk__in=result_qs) | Q(pk__in=child_qs))
                    .values_list("pk", flat=True)
                )

        return result_qs if result_qs is not None else self._all_concept_ids()

    def _evaluate_condition(self, condition):
        """Evaluate a single facet condition and return a QuerySet of PKs."""
        facet = condition.get("facet")

        if facet not in VALID_FACETS:
            return self._all_concept_ids().none()

        handler = getattr(self, f"_facet_{facet}", None)
        if handler is None:
            return self._all_concept_ids().none()

        result_qs = handler(condition)

        if condition.get("negated"):
            # Exclude matched PKs from the full concept set via subquery.
            return self._all_concept_ids().exclude(pk__in=result_qs)

        return result_qs

    MATCH_MODE_LOOKUPS = {
        "contains": "icontains",
        "exact": "iexact",
        "starts_with": "istartswith",
        "ends_with": "iendswith",
    }

    def _text_filter(self, field, value, match_mode="contains"):
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
            filters &= Q(
                **{
                    f"data__{CONCEPT_NAME_TYPE_NODE}__contains": [
                        {"labels": [{"list_item_id": label_type}]}
                    ]
                }
            )

        language = condition.get("language")
        if language:
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

        return (
            TileModel.objects.filter(
                Q(
                    nodegroup_id=CONCEPT_NAME_NODEGROUP,
                    **{f"data__{CONCEPT_NAME_LANGUAGE_NODE}": language},
                )
                | Q(
                    nodegroup_id=STATEMENT_NODEGROUP,
                    **{f"data__{STATEMENT_LANGUAGE_NODE}": language},
                )
            )
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

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

    def _normalize_target_ids(self, value):
        """Normalize a value that may be a single ID string or list of IDs."""
        if isinstance(value, list):
            return [tid for tid in value if tid]
        if value:
            return [value]
        return []

    def _direct_children_of(self, parent_ids):
        """Return a QuerySet of resource-instance PKs whose broader is one of parent_ids."""
        q_filter = Q()
        for parent_id in parent_ids:
            q_filter |= Q(
                **{
                    f"data__{CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID}__contains": [
                        {"resourceId": str(parent_id)}
                    ]
                }
            )
        return (
            TileModel.objects.filter(nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP)
            .filter(q_filter)
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

    def _direct_parents_of(self, child_ids):
        """Return a QuerySet of resource-instance PKs that are the broader of any child in child_ids."""
        return (
            TileModel.objects.filter(
                nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
                resourceinstance_id__in=child_ids,
            )
            .annotate(
                broader_id=RawSQL(
                    "(jsonb_array_elements(tiledata->%s) ->> 'resourceId')::uuid",
                    [CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID],
                )
            )
            .values_list("broader_id", flat=True)
            .distinct()
        )

    def _cascade_descendants(self, seed_ids):
        """Return all descendant concept IDs via a single recursive CTE.

        The edge_list CTE extracts every (child, parent) pair from
        classification tiles exactly once.  The recursive term then joins
        against that in-memory edge list using simple UUID equality, so the
        tiles table is never scanned again during recursion.  This avoids the
        O(depth × table_size) cost of the previous approach where the full
        tiles table was re-scanned at each recursion level.
        """
        seed_id_strings = [str(sid) for sid in seed_ids]
        node_id = str(CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID)
        nodegroup_id = str(CLASSIFICATION_STATUS_NODEGROUP)
        sql = """
            WITH RECURSIVE
            edge_list AS MATERIALIZED (
                SELECT
                    t.resourceinstanceid::uuid AS child_id,
                    (elem ->> 'resourceId')::uuid AS parent_id
                FROM tiles t
                CROSS JOIN LATERAL jsonb_array_elements(t.tiledata -> %s) AS elem
                WHERE t.nodegroupid = %s::uuid
                  AND elem ->> 'resourceId' IS NOT NULL
            ),
            descendants(concept_id) AS (
                SELECT child_id AS concept_id
                FROM edge_list
                WHERE parent_id::text = ANY(%s)
              UNION
                SELECT e.child_id
                FROM edge_list e
                JOIN descendants d ON e.parent_id = d.concept_id
            )
            SELECT concept_id FROM descendants
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [node_id, nodegroup_id, seed_id_strings])
            return [row[0] for row in cursor.fetchall()]

    def _cascade_ancestors(self, seed_ids):
        """Return all ancestor concept IDs via a single recursive CTE.

        The edge_list CTE extracts every (child, parent) pair from
        classification tiles exactly once.  The recursive term then joins
        against that in-memory edge list using simple UUID equality, so the
        tiles table is never scanned again during recursion.  This avoids the
        O(depth × table_size) cost of the previous approach where the full
        tiles table was re-scanned at each recursion level.
        """
        seed_id_strings = [str(sid) for sid in seed_ids]
        node_id = str(CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID)
        nodegroup_id = str(CLASSIFICATION_STATUS_NODEGROUP)
        sql = """
            WITH RECURSIVE
            edge_list AS MATERIALIZED (
                SELECT
                    t.resourceinstanceid::uuid AS child_id,
                    (elem ->> 'resourceId')::uuid AS parent_id
                FROM tiles t
                CROSS JOIN LATERAL jsonb_array_elements(t.tiledata -> %s) AS elem
                WHERE t.nodegroupid = %s::uuid
                  AND elem ->> 'resourceId' IS NOT NULL
            ),
            ancestors(concept_id) AS (
                SELECT parent_id AS concept_id
                FROM edge_list
                WHERE child_id::text = ANY(%s)
              UNION
                SELECT e.parent_id
                FROM edge_list e
                JOIN ancestors a ON e.child_id = a.concept_id
            )
            SELECT concept_id FROM ancestors WHERE concept_id IS NOT NULL
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [node_id, nodegroup_id, seed_id_strings])
            return [row[0] for row in cursor.fetchall()]

    def _facet_relationship_hierarchical(self, condition):
        """Find concepts with a hierarchical relationship to given concept(s).

        When cascade is True the search traverses the full hierarchy rather than
        matching only direct broader/narrower relationships.  Cascade traversal
        uses a recursive CTE executed in a single database round-trip.
        """
        target_ids = self._normalize_target_ids(condition.get("value"))
        direction = condition.get("direction", "broader")
        cascade = condition.get("cascade", False)

        if not target_ids:
            return self._all_concept_ids()

        if direction == "broader":
            if cascade:
                descendant_ids = self._cascade_descendants(target_ids)
                if not descendant_ids:
                    return ResourceInstance.objects.none().values_list("pk", flat=True)
                return ResourceInstance.objects.filter(
                    graph_id=CONCEPTS_GRAPH_ID,
                    resourceinstanceid__in=descendant_ids,
                ).values_list("pk", flat=True)
            else:
                return self._direct_children_of(target_ids)
        else:  # narrower
            if cascade:
                ancestor_ids = self._cascade_ancestors(target_ids)
                if not ancestor_ids:
                    return ResourceInstance.objects.none().values_list("pk", flat=True)
                return ResourceInstance.objects.filter(
                    graph_id=CONCEPTS_GRAPH_ID,
                    resourceinstanceid__in=ancestor_ids,
                ).values_list("pk", flat=True)
            else:
                return ResourceInstance.objects.filter(
                    graph_id=CONCEPTS_GRAPH_ID,
                    resourceinstanceid__in=self._direct_parents_of(target_ids),
                ).values_list("pk", flat=True)

    def _facet_relationship_associated(self, condition):
        """Find concepts associated with given concept(s)."""
        target_ids = self._normalize_target_ids(condition.get("value"))
        if not target_ids:
            return self._all_concept_ids()

        # Forward: concepts that list any target_id in their relation_status.
        forward_q = Q()
        for target_id in target_ids:
            forward_q |= Q(
                **{
                    f"data__{RELATION_STATUS_ASCRIBED_COMPARATE_NODEID}__contains": [
                        {"resourceId": target_id}
                    ]
                }
            )
        forward_qs = (
            TileModel.objects.filter(
                nodegroup_id=RELATION_STATUS_NODEGROUP,
            )
            .filter(forward_q)
            .values("resourceinstance_id")
        )

        # Reverse: extract IDs from target_ids' relation_status tiles via DB.
        reverse_ids_qs = (
            TileModel.objects.filter(
                nodegroup_id=RELATION_STATUS_NODEGROUP,
                resourceinstance_id__in=target_ids,
            )
            .annotate(
                comparate_id=RawSQL(
                    "(jsonb_array_elements(tiledata->%s) ->> 'resourceId')::uuid",
                    [RELATION_STATUS_ASCRIBED_COMPARATE_NODEID],
                )
            )
            .values("comparate_id")
        )

        return (
            ResourceInstance.objects.filter(
                graph_id=CONCEPTS_GRAPH_ID,
            )
            .filter(
                Q(resourceinstanceid__in=forward_qs.values("resourceinstance_id"))
                | Q(resourceinstanceid__in=reverse_ids_qs.values("comparate_id"))
            )
            .values_list("pk", flat=True)
        )

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

    def _facet_top_concept(self, condition):
        """Find concepts that are top concepts, optionally within a scheme."""
        scheme_id = condition.get("value")

        tiles = TileModel.objects.filter(nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP)
        if scheme_id:
            tiles = tiles.filter(
                **{
                    f"data__{TOP_CONCEPT_OF_NODE_AND_NODEGROUP}__contains": [
                        {"resourceId": scheme_id}
                    ]
                }
            )

        return tiles.values_list("resourceinstance_id", flat=True).distinct()

    def _facet_scheme(self, condition):
        """Find concepts that belong to a specific scheme."""
        scheme_id = condition.get("value")
        if not scheme_id:
            return self._all_concept_ids()

        return (
            TileModel.objects.filter(
                Q(
                    nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
                    **{
                        f"data__{CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}__contains": [
                            {"resourceId": scheme_id}
                        ]
                    },
                )
                | Q(
                    nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
                    **{
                        f"data__{TOP_CONCEPT_OF_NODE_AND_NODEGROUP}__contains": [
                            {"resourceId": scheme_id}
                        ]
                    },
                )
            )
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

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
            return self._all_concept_ids().none()

        try:
            concept_set = ConceptSet.objects.get(pk=set_id, user=self.user)
        except ConceptSet.DoesNotExist:
            return self._all_concept_ids().none()

        return concept_set.members.values_list("concept_id", flat=True)

    def _facet_attribution_source(self, condition):
        """Find concepts whose labels or notes are attributed to a specific source.

        A source is a textual work referenced via the data_assignment_object_used node
        on both appellative_status (label) and statement (note) tiles.  When the
        match_mode is 'exists', returns all concepts that have any source attributed
        to at least one label or note.
        """
        resource_id = condition.get("value", "").strip()
        match_mode = condition.get("match_mode", "")

        if match_mode == "exists":
            filters = Q(
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                **{
                    f"data__{CONCEPT_NAME_DATA_ASSIGNMENT_OBJ_USED_NODE}__contains": [
                        {}
                    ]
                },
            ) | Q(
                nodegroup_id=STATEMENT_NODEGROUP,
                **{f"data__{STATEMENT_DATA_ASSIGNMENT_OBJ_USED_NODE}__contains": [{}]},
            )
        elif resource_id:
            filters = Q(
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                **{
                    f"data__{CONCEPT_NAME_DATA_ASSIGNMENT_OBJ_USED_NODE}__contains": [
                        {"resourceId": resource_id}
                    ]
                },
            ) | Q(
                nodegroup_id=STATEMENT_NODEGROUP,
                **{
                    f"data__{STATEMENT_DATA_ASSIGNMENT_OBJ_USED_NODE}__contains": [
                        {"resourceId": resource_id}
                    ]
                },
            )
        else:
            return self._all_concept_ids()

        return (
            TileModel.objects.filter(filters)
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )

    def _facet_attribution_contributor(self, condition):
        """Find concepts whose labels or notes are attributed to a specific contributor.

        A contributor is a person or organization referenced via the
        data_assignment_actor node on both appellative_status (label) and statement
        (note) tiles.  When the match_mode is 'exists', returns all concepts that
        have any contributor attributed to at least one label or note.
        """
        resource_id = condition.get("value", "").strip()
        match_mode = condition.get("match_mode", "")

        if match_mode == "exists":
            filters = Q(
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                **{f"data__{CONCEPT_NAME_DATA_ASSIGNMENT_ACTOR_NODE}__contains": [{}]},
            ) | Q(
                nodegroup_id=STATEMENT_NODEGROUP,
                **{f"data__{STATEMENT_DATA_ASSIGNMENT_ACTOR_NODE}__contains": [{}]},
            )
        elif resource_id:
            filters = Q(
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                **{
                    f"data__{CONCEPT_NAME_DATA_ASSIGNMENT_ACTOR_NODE}__contains": [
                        {"resourceId": resource_id}
                    ]
                },
            ) | Q(
                nodegroup_id=STATEMENT_NODEGROUP,
                **{
                    f"data__{STATEMENT_DATA_ASSIGNMENT_ACTOR_NODE}__contains": [
                        {"resourceId": resource_id}
                    ]
                },
            )
        else:
            return self._all_concept_ids()

        return (
            TileModel.objects.filter(filters)
            .values_list("resourceinstance_id", flat=True)
            .distinct()
        )
