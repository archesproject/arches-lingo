from collections import defaultdict

from django.contrib.postgres.expressions import ArraySubquery
from django.core.cache import caches
from django.db.models import CharField, Exists, F, OuterRef, Value
from django.db.models.expressions import CombinedExpression
from django.utils.translation import gettext_lazy as _

from arches.app.models.models import (
    Relation,
    ResourceInstance,
    TileModel,
    Value as ConceptValue,
)

from arches_lingo.const import (
    SCHEMES_GRAPH_ID,
    TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
    CLASSIFICATION_STATUS_NODEGROUP,
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_TYPE_NODE,
    HIDDEN_LABEL_VALUE_ID,
    LANGUAGE_CONCEPT_ID,
    SCHEME_NAME_NODEGROUP,
    SCHEME_NAME_CONTENT_NODE,
    SCHEME_NAME_LANGUAGE_NODE,
    SCHEME_NAME_TYPE_NODE,
    PREF_LABEL_VALUE_ID,
    ALT_LABEL_VALUE_ID,
)
from arches_lingo.utils.query_expressions import JsonbArrayElements

TOP_CONCEPT_OF_LOOKUP = f"data__{TOP_CONCEPT_OF_NODE_AND_NODEGROUP}"
BROADER_LOOKUP = f"data__{CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID}"

cache = caches["lingo"]


class ConceptBuilder:
    def __init__(self):
        self.schemes = ResourceInstance.objects.none()

        # key=concept valueid (str) val=language code
        self.language_concepts: dict[str:str] = {}
        # key=scheme resourceid (str) val=set of concept resourceids (str)
        self.top_concepts: dict[str : set[str]] = defaultdict(set)
        # key=concept resourceid (str) val=set of concept resourceids (str)
        self.narrower_concepts: dict[str : set[str]] = defaultdict(set)
        # key=resourceid (str) val=list of label dicts
        self.labels: dict[str : list[dict]] = defaultdict(set)

        # Maps representing a reverse (leaf-first) tree
        # key=resourceid (str) val=set of concept resourceids (str)
        self.broader_concepts: dict[str : set[str]] = defaultdict(set)
        # key=resourceid (str) val=set of scheme resourceids (str)
        self.schemes_by_top_concept: dict[str : set[str]] = defaultdict(set)

        self.read_from_cache()

        # Not currently cached because written to during serialization.
        self.polyhierarchical_concepts = set()

    def read_from_cache(self):
        from_cache = cache.get_many(
            [
                "language_concepts",
                "top_concepts",
                "narrower_concepts",
                "schemes",
                "labels",
                "broader_concepts",
                "schemes_by_top_concept",
            ]
        )
        try:
            self.language_concepts = from_cache["language_concepts"]
            self.top_concepts = from_cache["top_concepts"]
            self.narrower_concepts = from_cache["narrower_concepts"]
            self.schemes = from_cache["schemes"]
            self.labels = from_cache["labels"]
            self.broader_concepts = from_cache["broader_concepts"]
            self.schemes_by_top_concept = from_cache["schemes_by_top_concept"]
        except KeyError:
            self.rebuild_cache()

    def rebuild_cache(self):
        self.language_concepts_map()
        self.top_concepts_map()
        self.narrower_concepts_map()
        self.populate_schemes()

        cache.set("language_concepts", self.language_concepts)
        cache.set("top_concepts", self.top_concepts)
        cache.set("narrower_concepts", self.narrower_concepts)
        cache.set("schemes", self.schemes)
        cache.set("labels", self.labels)
        # Reverse trees.
        cache.set("broader_concepts", self.broader_concepts)
        cache.set("schemes_by_top_concept", self.schemes_by_top_concept)

    @staticmethod
    def human_label_type(value_id):
        if value_id == PREF_LABEL_VALUE_ID:
            return "prefLabel"
        if value_id == ALT_LABEL_VALUE_ID:
            return "altLabel"
        if value_id == HIDDEN_LABEL_VALUE_ID:
            return "hiddenLabel"
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
        else:
            # Annotating a Tile
            outer = OuterRef("resourceinstance_id")
            nodegroup_id = CONCEPT_NAME_NODEGROUP

        return ArraySubquery(
            TileModel.objects.filter(
                resourceinstance_id=outer, nodegroup_id=nodegroup_id
            ).values("data")
        )

    def language_concepts_map(self):
        language_preflabels = ConceptValue.objects.filter(
            Exists(
                Relation.objects.filter(
                    conceptfrom=LANGUAGE_CONCEPT_ID,
                    conceptto=OuterRef("concept_id"),
                    relationtype="narrower",
                )
            ),
            valuetype="prefLabel",
        )
        for language_label in language_preflabels:
            self.language_concepts[str(language_label.pk)] = language_label.value

    def top_concepts_map(self):
        top_concept_of_tiles = (
            TileModel.objects.filter(nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP)
            .annotate(top_concept_of=self.resources_from_tiles(TOP_CONCEPT_OF_LOOKUP))
            .annotate(labels=self.labels_subquery(CONCEPT_NAME_NODEGROUP))
            .values("resourceinstance_id", "top_concept_of", "labels")
        )
        for tile in top_concept_of_tiles:
            scheme_id = tile["top_concept_of"]
            top_concept_id = str(tile["resourceinstance_id"])
            self.top_concepts[scheme_id].add(top_concept_id)
            self.schemes_by_top_concept[top_concept_id].add(scheme_id)
            self.labels[top_concept_id] = tile["labels"]

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

    def populate_schemes(self):
        self.schemes = ResourceInstance.objects.filter(
            graph_id=SCHEMES_GRAPH_ID
        ).annotate(labels=self.labels_subquery(SCHEME_NAME_NODEGROUP))

    def serialize_scheme(self, scheme: ResourceInstance, *, children=True):
        scheme_id: str = str(scheme.pk)
        data = {
            "id": scheme_id,
            "labels": [self.serialize_scheme_label(label) for label in scheme.labels],
        }
        if children:
            data["top_concepts"] = [
                self.serialize_concept(concept_id)
                for concept_id in self.top_concepts[scheme_id]
            ]
        return data

    def serialize_scheme_label(self, label_tile: dict):
        lang_code = self.language_concepts[label_tile[SCHEME_NAME_LANGUAGE_NODE][0]]
        localized_string_objs = label_tile[SCHEME_NAME_CONTENT_NODE].values()
        try:
            value = next(iter(localized_string_objs))["value"]
        except (StopIteration, KeyError):
            value = "Unknown"
        return {
            "valuetype_id": self.human_label_type(label_tile[SCHEME_NAME_TYPE_NODE]),
            "language_id": lang_code,
            "value": value,
        }

    def serialize_concept(self, conceptid: str, *, parents=False, children=True):
        data = {
            "id": conceptid,
            "labels": [
                self.serialize_concept_label(label) for label in self.labels[conceptid]
            ],
        }
        if children:
            data["narrower"] = [
                self.serialize_concept(conceptid)
                for conceptid in self.narrower_concepts[conceptid]
            ]
        if parents:
            path = self.add_broader_concept_recursive([], conceptid)
            scheme_id, parent_concept_ids = path[0], path[1:]
            if len(parent_concept_ids) > 1:
                self.polyhierarchical_concepts.add(conceptid)
            schemes = [scheme for scheme in self.schemes if str(scheme.pk) == scheme_id]
            data["parents"] = [self.serialize_scheme(schemes[0], children=False)] + [
                self.serialize_concept(parent_id, children=False)
                for parent_id in parent_concept_ids
            ]

            self_and_parent_ids = set([conceptid] + parent_concept_ids)
            data["polyhierarchical"] = bool(
                self_and_parent_ids.intersection(self.polyhierarchical_concepts)
            )

        return data

    def add_broader_concept_recursive(self, working_parent_list, conceptid):
        # TODO: sort on sortorder at higher stacklevel once captured in original data.
        broader_concepts = sorted(self.broader_concepts[conceptid])
        try:
            first_broader_conceptid = broader_concepts[0]
        except IndexError:
            # TODO: sort here too.
            schemes = sorted(self.schemes_by_top_concept[conceptid])
            working_parent_list.insert(0, schemes[0])
            return working_parent_list
        working_parent_list.insert(0, first_broader_conceptid)
        return self.add_broader_concept_recursive(
            working_parent_list, first_broader_conceptid
        )

    def serialize_concept_label(self, label_tile: dict):
        lang_code = self.language_concepts[label_tile[CONCEPT_NAME_LANGUAGE_NODE][0]]
        localized_string_objs = label_tile[CONCEPT_NAME_CONTENT_NODE].values()
        try:
            value = next(iter(localized_string_objs))["value"]
        except (StopIteration, KeyError):
            value = "Unknown"
        return {
            "valuetype_id": self.human_label_type(label_tile[CONCEPT_NAME_TYPE_NODE]),
            "language_id": lang_code,
            "value": value,
        }
