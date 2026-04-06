import logging
from collections import defaultdict

from django.contrib.postgres.expressions import ArraySubquery
from django.db import connection
from django.db.models import CharField, F, OuterRef, Value
from django.db.models.expressions import CombinedExpression
from django.utils.translation import gettext as _

from arches.app.models.models import (
    Language,
    ResourceInstance,
    ResourceInstanceLifecycleState,
    TileModel,
)

logger = logging.getLogger(__name__)

from arches_lingo.const import (
    ALT_LABEL_URI,
    SCHEMES_GRAPH_ID,
    TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
    CLASSIFICATION_STATUS_NODEGROUP,
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    CONCEPT_TYPE_NODEGROUP,
    CONCEPT_TYPE_NODEID,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_TYPE_NODE,
    GUIDE_TERM_URI,
    HIDDEN_LABEL_URI,
    PREF_LABEL_URI,
    SCHEME_NAME_NODEGROUP,
    SCHEME_NAME_CONTENT_NODE,
    SCHEME_NAME_LANGUAGE_NODE,
    SCHEME_NAME_TYPE_NODE,
)

from arches_lingo.query_expressions import JsonbArrayElements


TOP_CONCEPT_OF_LOOKUP = f"data__{TOP_CONCEPT_OF_NODE_AND_NODEGROUP}"
BROADER_LOOKUP = f"data__{CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID}"
CONCEPT_TYPE_LOOKUP = f"data__{CONCEPT_TYPE_NODEID}"


class ConceptBuilder:
    def __init__(
        self,
        concept_ids: list[str] | None = None,
        *,
        include_parents: bool = False,
        shallow: bool = False,
    ):
        self.schemes = ResourceInstance.objects.none()
        self.schemes_by_id: dict[str, ResourceInstance] = {}

        self.top_concepts: dict[str, set[str]] = defaultdict(set)
        self.narrower_concepts: dict[str, set[str]] = defaultdict(set)
        self.labels: dict[str, list[dict]] = defaultdict(list)

        self.broader_concepts: dict[str, set[str]] = defaultdict(set)
        self.schemes_by_top_concept: dict[str, set[str]] = defaultdict(set)

        self.polyhierarchical_concepts = set()
        self.guide_term_concepts: set[str] = set()
        self.language_lookup = {lang.code: lang.name for lang in Language.objects.all()}

        self.resource_instance_lifecycle_state_ids_by_resource_instance_id: dict[
            str, str | None
        ] = {}
        self.lifecycle_state_names_by_id: dict[str, str] = {}

        if concept_ids is None:
            self.top_concepts_map()
            top_concept_ids = list(self.labels.keys())
            if not shallow:
                self.narrower_concepts_map()
            else:
                self.batch_check_has_narrower(top_concept_ids)
            self.populate_guide_term_concepts(top_concept_ids if shallow else None)
            self.populate_schemes()
            self.populate_resource_instance_lifecycle_state_ids(
                scheme_ids=list(self.schemes_by_id.keys()),
                concept_ids=top_concept_ids,
            )
            return

        if include_parents:
            self.build_scoped_parents(concept_ids)
            return

        self.populate_concept_labels(concept_ids)
        self.populate_resource_instance_lifecycle_state_ids(
            scheme_ids=list(self.schemes_by_id.keys()),
            concept_ids=concept_ids,
        )
        self.populate_guide_term_concepts(concept_ids)

    @staticmethod
    def find_valuetype_id_from_uri(uri):
        if uri == PREF_LABEL_URI:
            return "prefLabel"
        if uri == ALT_LABEL_URI:
            return "altLabel"
        if uri == HIDDEN_LABEL_URI:
            return "hidden"
        return "unknown"

    @staticmethod
    def resources_from_tiles(lookup_expression: str):
        return CombinedExpression(
            JsonbArrayElements(F(lookup_expression)),
            "->>",
            Value("resourceId"),
            output_field=CharField(),
        )

    @staticmethod
    def labels_subquery(label_nodegroup):
        if label_nodegroup == SCHEME_NAME_NODEGROUP:
            # Annotating a ResourceInstance
            outer = OuterRef("resourceinstanceid")
            nodegroup_id = SCHEME_NAME_NODEGROUP
            type_node = SCHEME_NAME_TYPE_NODE
            language_node = SCHEME_NAME_LANGUAGE_NODE
        else:
            # Annotating a Tile
            outer = OuterRef("resourceinstance_id")
            nodegroup_id = CONCEPT_NAME_NODEGROUP
            type_node = CONCEPT_NAME_TYPE_NODE
            language_node = CONCEPT_NAME_LANGUAGE_NODE

        return ArraySubquery(
            TileModel.objects.filter(
                resourceinstance_id=outer, nodegroup_id=nodegroup_id
            )
            .exclude(**{f"data__{type_node}": None})
            .exclude(**{f"data__{language_node}": None})
            .values("data")
        )

    def populate_schemes(self, scheme_ids: list[str] | None = None):
        schemes_query = ResourceInstance.objects.filter(graph_id=SCHEMES_GRAPH_ID)
        if scheme_ids is not None:
            schemes_query = schemes_query.filter(pk__in=scheme_ids)

        schemes_list = list(
            schemes_query.annotate(labels=self.labels_subquery(SCHEME_NAME_NODEGROUP))
        )
        self.schemes = schemes_list
        self.schemes_by_id = {str(scheme.pk): scheme for scheme in schemes_list}

    def populate_resource_instance_lifecycle_state_ids(
        self, *, scheme_ids: list[str], concept_ids: list[str]
    ):
        resource_instance_ids = [*scheme_ids, *concept_ids]
        self.resource_instance_lifecycle_state_ids_by_resource_instance_id = {}
        self.lifecycle_state_names_by_id = {}

        if not resource_instance_ids:
            return

        self.resource_instance_lifecycle_state_ids_by_resource_instance_id = {
            str(resource_instance_id): (
                str(lifecycle_state_id) if lifecycle_state_id else None
            )
            for resource_instance_id, lifecycle_state_id in (
                ResourceInstance.objects.filter(
                    pk__in=resource_instance_ids
                ).values_list(
                    "resourceinstanceid", "resource_instance_lifecycle_state_id"
                )
            )
        }

        unique_state_ids = {
            state_id
            for state_id in self.resource_instance_lifecycle_state_ids_by_resource_instance_id.values()
            if state_id is not None
        }
        if unique_state_ids:
            self.lifecycle_state_names_by_id = {
                str(state_id): str(state_name)
                for state_id, state_name in ResourceInstanceLifecycleState.objects.filter(
                    pk__in=unique_state_ids
                ).values_list(
                    "id", "name"
                )
            }

    def lookup_scheme(self, scheme_id: str):
        return self.schemes_by_id.get(scheme_id)

    def populate_concept_labels(self, concept_ids: list[str]):
        label_tiles = (
            TileModel.objects.filter(
                nodegroup_id=CONCEPT_NAME_NODEGROUP, resourceinstance_id__in=concept_ids
            )
            .exclude(**{f"data__{CONCEPT_NAME_TYPE_NODE}": None})
            .exclude(**{f"data__{CONCEPT_NAME_LANGUAGE_NODE}": None})
            .values("resourceinstance_id", "data")
        )
        for tile in label_tiles.iterator():
            concept_id = str(tile["resourceinstance_id"])
            self.labels[concept_id].append(tile["data"])

    @classmethod
    def for_concept_children(cls, parent_concept_id: str) -> "ConceptBuilder":
        """Build a ConceptBuilder loaded with the direct children of a concept.

        The resulting instance has `narrower_concepts`, `labels`,
        `schemes_by_top_concept`, and `guide_term_concepts` populated only for
        the immediate children of `parent_concept_id`.

        Uses separate batch queries instead of correlated subqueries for
        labels and has_children to avoid O(N * table_scan) execution plans.
        """
        builder = cls.__new__(cls)
        builder.schemes = ResourceInstance.objects.none()
        builder.schemes_by_id = {}
        builder.top_concepts = defaultdict(set)
        builder.narrower_concepts = defaultdict(set)
        builder.labels = defaultdict(list)
        builder.broader_concepts = defaultdict(set)
        builder.schemes_by_top_concept = defaultdict(set)
        builder.polyhierarchical_concepts = set()
        builder.guide_term_concepts = set()
        builder.language_lookup = {
            lang.code: lang.name for lang in Language.objects.all()
        }
        builder.resource_instance_lifecycle_state_ids_by_resource_instance_id = {}
        builder.lifecycle_state_names_by_id = {}

        # Query 1: Get direct child resource instance IDs.
        child_ids: set[str] = set()
        child_tiles = TileModel.objects.filter(
            nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
            **{f"{BROADER_LOOKUP}__contains": [{"resourceId": parent_concept_id}]},
        ).values_list("resourceinstance_id", flat=True)
        for resource_instance_id in child_tiles.iterator():
            child_id = str(resource_instance_id)
            child_ids.add(child_id)
            builder.narrower_concepts[parent_concept_id].add(child_id)

        if not child_ids:
            return builder

        # Query 2: Batch-fetch labels for all children at once.
        builder.populate_concept_labels(list(child_ids))

        # Query 3: Batch-check which children have their own narrower
        # concepts. Uses a single unnest + EXISTS query so the GIN index
        # on the broader-concept JSONB column is hit once per child_id
        # instead of running a correlated subquery per outer row.
        builder.batch_check_has_narrower(list(child_ids))

        # Track which children are top concepts of any scheme.
        top_concept_of_tiles = (
            TileModel.objects.filter(
                nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
                resourceinstance_id__in=child_ids,
            )
            .annotate(
                top_concept_of=builder.resources_from_tiles(TOP_CONCEPT_OF_LOOKUP)
            )
            .values("resourceinstance_id", "top_concept_of")
        )
        for tile in top_concept_of_tiles.iterator():
            top_concept_id = str(tile["resourceinstance_id"])
            builder.schemes_by_top_concept[top_concept_id].add(tile["top_concept_of"])

        builder.populate_guide_term_concepts(list(child_ids))
        builder.populate_resource_instance_lifecycle_state_ids(
            scheme_ids=[],
            concept_ids=list(child_ids),
        )

        return builder

    def top_concepts_map(self):
        top_concept_of_tiles = (
            TileModel.objects.filter(nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP)
            .annotate(top_concept_of=self.resources_from_tiles(TOP_CONCEPT_OF_LOOKUP))
            .annotate(labels=self.labels_subquery(CONCEPT_NAME_NODEGROUP))
            .values("resourceinstance_id", "top_concept_of", "labels")
        )
        for tile in top_concept_of_tiles.iterator():
            scheme_id = tile["top_concept_of"]
            top_concept_id = str(tile["resourceinstance_id"])
            self.top_concepts[scheme_id].add(top_concept_id)
            self.schemes_by_top_concept[top_concept_id].add(scheme_id)
            self.labels[top_concept_id] = tile["labels"]

    def narrower_exists_map(self):
        """Populate `narrower_concepts` to record which concepts have children.

        Used by the shallow initial tree load to flag every concept that has at
        least one narrower concept, without loading the full child set.  The
        stored value is a non-empty set when a parent has at least one child.

        For the per-concept children endpoint, `has_narrower` is now computed
        inline via an EXISTS subquery in `for_concept_children`, which avoids
        the OR-of-containment-checks approach that was very slow for nodes
        with many children.
        """
        broader_tiles = (
            TileModel.objects.filter(
                nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
            )
            .annotate(broader_concept=self.resources_from_tiles(BROADER_LOOKUP))
            .values("resourceinstance_id", "broader_concept")
        )
        for tile in broader_tiles.iterator():
            broader_concept_id = tile["broader_concept"]
            child_id = str(tile["resourceinstance_id"])
            if broader_concept_id:
                self.narrower_concepts[broader_concept_id].add(child_id)

    def batch_check_has_narrower(self, concept_ids: list[str]) -> None:
        """Check which of the given concept IDs have narrower concepts.

        Uses a single unnest + EXISTS query against the GIN-indexed broader
        concept column, avoiding a full scan of all classification tiles.
        """
        if not concept_ids:
            return

        _tile_table = TileModel._meta.db_table
        _nodegroup_col = TileModel._meta.get_field("nodegroup").column
        _data_col = TileModel._meta.get_field("data").column
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT concept_id
                FROM unnest(%(concept_ids)s::text[]) AS concept_id
                WHERE EXISTS (
                    SELECT 1
                    FROM "{_tile_table}" sub
                    WHERE sub."{_nodegroup_col}" = %(nodegroup)s::uuid
                      AND sub."{_data_col}"->%(node_id)s
                          @> jsonb_build_array(
                              jsonb_build_object('resourceId', concept_id)
                          )
                )
                """,
                {
                    "concept_ids": concept_ids,
                    "nodegroup": str(CLASSIFICATION_STATUS_NODEGROUP),
                    "node_id": str(
                        CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID
                    ),
                },
            )
            for (concept_id,) in cursor.fetchall():
                self.narrower_concepts[concept_id].add("__narrower_exists__")

    def narrower_concepts_map(self):
        broader_concept_tiles = (
            TileModel.objects.filter(nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP)
            .annotate(broader_concept=self.resources_from_tiles(BROADER_LOOKUP))
            .annotate(labels=self.labels_subquery(CONCEPT_NAME_NODEGROUP))
            .values("resourceinstance_id", "broader_concept", "labels")
        )
        for tile in broader_concept_tiles.iterator():
            broader_concept_id = tile["broader_concept"]
            narrower_concept_id: str = str(tile["resourceinstance_id"])
            self.narrower_concepts[broader_concept_id].add(narrower_concept_id)
            self.broader_concepts[narrower_concept_id].add(broader_concept_id)
            self.labels[narrower_concept_id] = tile["labels"]

    def build_scoped_parents(self, concept_ids: list[str]):
        closure_concept_ids: set[str] = set(concept_ids)
        frontier_concept_ids: set[str] = set(concept_ids)

        while frontier_concept_ids:
            broader_concept_tiles = (
                TileModel.objects.filter(
                    nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
                    resourceinstance_id__in=frontier_concept_ids,
                )
                .annotate(broader_concept=self.resources_from_tiles(BROADER_LOOKUP))
                .values("resourceinstance_id", "broader_concept")
            )

            next_frontier_concept_ids: set[str] = set()

            for tile in broader_concept_tiles.iterator():
                broader_concept_id = tile["broader_concept"]
                if not broader_concept_id:
                    continue

                narrower_concept_id = str(tile["resourceinstance_id"])
                broader_concept_id_string = str(broader_concept_id)

                self.broader_concepts[narrower_concept_id].add(
                    broader_concept_id_string
                )

                if broader_concept_id_string not in closure_concept_ids:
                    closure_concept_ids.add(broader_concept_id_string)
                    next_frontier_concept_ids.add(broader_concept_id_string)

            top_concept_of_tiles = (
                TileModel.objects.filter(
                    nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
                    resourceinstance_id__in=frontier_concept_ids,
                )
                .annotate(
                    top_concept_of=self.resources_from_tiles(TOP_CONCEPT_OF_LOOKUP)
                )
                .values("resourceinstance_id", "top_concept_of")
            )

            for tile in top_concept_of_tiles.iterator():
                scheme_id = tile["top_concept_of"]
                if not scheme_id:
                    continue

                top_concept_id = str(tile["resourceinstance_id"])
                self.schemes_by_top_concept[top_concept_id].add(str(scheme_id))

            frontier_concept_ids = next_frontier_concept_ids

        scheme_ids = set()
        for scheme_id_set in self.schemes_by_top_concept.values():
            scheme_ids |= scheme_id_set

        self.populate_schemes(list(scheme_ids))
        self.populate_concept_labels(list(closure_concept_ids))
        self.populate_resource_instance_lifecycle_state_ids(
            scheme_ids=list(self.schemes_by_id.keys()),
            concept_ids=list(closure_concept_ids),
        )
        self.populate_guide_term_concepts(list(closure_concept_ids))

    def serialize_scheme(
        self, scheme: ResourceInstance, *, children=True, shallow=False
    ):
        scheme_id: str = str(scheme.pk)
        scheme_lifecycle_state_id = (
            self.resource_instance_lifecycle_state_ids_by_resource_instance_id.get(
                scheme_id
            )
        )
        data = {
            "id": scheme_id,
            "resource_instance_lifecycle_state_id": scheme_lifecycle_state_id,
            "resource_instance_lifecycle_state_name": self.lifecycle_state_names_by_id.get(
                scheme_lifecycle_state_id or ""
            ),
            "labels": [self.serialize_scheme_label(label) for label in scheme.labels],
        }
        if children:
            if shallow:
                data["top_concepts"] = [
                    self.serialize_concept_shallow(concept_id)
                    for concept_id in sorted(self.top_concepts[scheme_id])
                ]
            else:
                data["top_concepts"] = [
                    self.serialize_concept(concept_id)
                    for concept_id in sorted(self.top_concepts[scheme_id])
                ]
        return data

    def serialize_scheme_label(self, label_tile: dict):
        valuetype_id = self.find_valuetype_id_from_uri(
            label_tile[SCHEME_NAME_TYPE_NODE][0]["uri"]
        )
        language_id = label_tile[SCHEME_NAME_LANGUAGE_NODE]
        value = label_tile[SCHEME_NAME_CONTENT_NODE] or _("Unknown")
        return {
            "valuetype_id": valuetype_id,
            "language_id": language_id,
            "value": value,
        }

    @staticmethod
    def is_guide_term_tile(tile_data: dict) -> bool:
        """Check if a concept type tile has guide term type."""
        type_values = tile_data.get(CONCEPT_TYPE_NODEID)
        if not type_values:
            return False
        for ref in type_values:
            if ref.get("uri") == GUIDE_TERM_URI:
                return True
        return False

    def populate_guide_term_concepts(
        self, concept_ids: list[str] | None = None
    ) -> None:
        """Populate guide_term_concepts set from concept type tiles."""
        tiles = TileModel.objects.filter(
            nodegroup_id=CONCEPT_TYPE_NODEGROUP,
        ).exclude(**{CONCEPT_TYPE_LOOKUP: None})

        if concept_ids is not None:
            tiles = tiles.filter(resourceinstance_id__in=concept_ids)

        for tile in tiles.values("resourceinstance_id", "data").iterator():
            if self.is_guide_term_tile(tile["data"]):
                self.guide_term_concepts.add(str(tile["resourceinstance_id"]))

    def serialize_concept(self, conceptid: str, *, parents=False, children=True):
        concept_lifecycle_state_id = (
            self.resource_instance_lifecycle_state_ids_by_resource_instance_id.get(
                conceptid
            )
        )
        data = {
            "id": conceptid,
            "resource_instance_lifecycle_state_id": concept_lifecycle_state_id,
            "resource_instance_lifecycle_state_name": self.lifecycle_state_names_by_id.get(
                concept_lifecycle_state_id or ""
            ),
            "labels": [
                self.serialize_concept_label(label) for label in self.labels[conceptid]
            ],
            "guide_term": conceptid in self.guide_term_concepts,
            "top_concept": bool(self.schemes_by_top_concept.get(conceptid)),
        }
        if children:
            data["narrower"] = [
                self.serialize_concept(child_id)
                for child_id in sorted(self.narrower_concepts[conceptid])
            ]
        if parents:
            paths = self.find_paths_to_root([conceptid], conceptid)
            if len(paths) > 1:
                self.polyhierarchical_concepts.add(conceptid)

            data["parents"] = []
            for scheme_id, *parent_concept_ids in paths:
                scheme_object = self.lookup_scheme(scheme_id)
                if scheme_object is None:
                    # skip any path whose scheme_id isn't found
                    continue

                serialized_scheme = self.serialize_scheme(scheme_object, children=False)
                serialized_parent_concepts = [
                    self.serialize_concept(parent_concept_id, children=False)
                    for parent_concept_id in parent_concept_ids
                ]

                data["parents"].append([serialized_scheme] + serialized_parent_concepts)

            self_and_parent_ids = set()
            for path in paths:
                self_and_parent_ids |= set(path)
            data["polyhierarchical"] = bool(
                self_and_parent_ids.intersection(self.polyhierarchical_concepts)
            )

        return data

    def serialize_concept_shallow(self, conceptid: str) -> dict:
        """Serialize a concept without recursing into its children.

        Includes a `has_narrower` boolean so the frontend can show an expand
        toggle without having loaded the children yet.
        """
        concept_lifecycle_state_id = (
            self.resource_instance_lifecycle_state_ids_by_resource_instance_id.get(
                conceptid
            )
        )
        return {
            "id": conceptid,
            "resource_instance_lifecycle_state_id": concept_lifecycle_state_id,
            "resource_instance_lifecycle_state_name": self.lifecycle_state_names_by_id.get(
                concept_lifecycle_state_id or ""
            ),
            "labels": [
                self.serialize_concept_label(label) for label in self.labels[conceptid]
            ],
            "guide_term": conceptid in self.guide_term_concepts,
            "top_concept": bool(self.schemes_by_top_concept.get(conceptid)),
            "has_narrower": bool(self.narrower_concepts.get(conceptid)),
        }

    def find_paths_to_root(self, working_path, conceptid) -> list[list[str]]:
        """Return an array of paths (path: an array of scheme & concept ids).

        Skips any parent already present in working_path to avoid infinite
        recursion when cyclic broader-concept relationships exist in the data.
        """
        concept_and_scheme_parents = sorted(self.broader_concepts[conceptid]) + sorted(
            self.schemes_by_top_concept[conceptid]
        )

        collected_paths = []
        for parent in concept_and_scheme_parents:
            if parent in working_path:
                logger.warning(
                    _(
                        "Cycle detected in concept hierarchy: %s already appears in "
                        "the current path and will be skipped. Path: %s"
                    ),
                    parent,
                    working_path,
                )
                continue
            forked_path = working_path[:]
            forked_path.insert(0, parent)
            collected_paths.extend(self.find_paths_to_root(forked_path, parent))

        if concept_and_scheme_parents:
            return collected_paths
        return [working_path]

    def serialize_concept_label(self, label_tile: dict):
        valuetype_id = self.find_valuetype_id_from_uri(
            label_tile[CONCEPT_NAME_TYPE_NODE][0]["uri"]
        )
        language_id = label_tile[CONCEPT_NAME_LANGUAGE_NODE]
        value = label_tile[CONCEPT_NAME_CONTENT_NODE] or _("Unknown")
        return {
            "valuetype_id": valuetype_id,
            "language_id": language_id,
            "language": self.language_lookup.get(language_id, _("Unknown")),
            "value": value,
        }
