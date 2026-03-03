import json
import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core import management
from django.test import TestCase
from django.test.utils import captured_stdout
from django.urls import reverse

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models.models import ResourceInstance, ResourceXResource, TileModel
from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.utils.data_management.resource_graphs.importer import (
    import_graph as ResourceGraphImporter,
)

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_TYPE_NODE,
    CONCEPT_TYPE_NODE,
    CONCEPT_TYPE_NODEGROUP,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    CLASSIFICATION_STATUS_NODEGROUP,
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    GUIDE_TERM_URI,
    LABEL_LIST_ID,
    SCHEMES_GRAPH_ID,
    SCHEME_NAME_CONTENT_NODE,
    SCHEME_NAME_LANGUAGE_NODE,
    SCHEME_NAME_NODEGROUP,
    SCHEME_NAME_TYPE_NODE,
    TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
)
from arches_lingo.utils.concept_builder import ConceptBuilder


# python manage.py test tests.test_guide_term --settings="tests.test_settings"


class GuideTermTests(TestCase):
    """Tests that the guide term type is correctly identified and serialized."""

    graph_fixtures = ["Scheme.json", "Concept.json"]

    @classmethod
    def load_ontology(cls):
        path = Path(settings.APP_ROOT) / "pkg" / "ontologies" / "takin"
        management.call_command("load_ontology", source=path, verbosity=0)

    @classmethod
    def load_graphs(cls):
        path = Path(settings.APP_ROOT) / "pkg" / "graphs" / "resource_models"
        for file_path in cls.graph_fixtures:
            with captured_stdout(), open(path / file_path, "r") as f:
                archesfile = JSONDeserializer().deserialize(f)
                ResourceGraphImporter(archesfile["graph"], overwrite_graphs=True)

    @classmethod
    def setUpTestData(cls):
        cls.load_ontology()
        cls.load_graphs()
        cls.admin = User.objects.get(username="admin")

        reference = DataTypeFactory().get_instance("reference")
        label_config = {"controlledList": LABEL_LIST_ID}
        prefLabel_reference_dt = reference.transform_value_for_tile(
            "prefLabel", **label_config
        )

        # Create a scheme
        cls.scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Guide Term Test Scheme"
        )
        TileModel.objects.create(
            resourceinstance=cls.scheme,
            nodegroup_id=SCHEME_NAME_NODEGROUP,
            data={
                SCHEME_NAME_CONTENT_NODE: "Guide Term Test Scheme",
                SCHEME_NAME_TYPE_NODE: prefLabel_reference_dt,
                SCHEME_NAME_LANGUAGE_NODE: "en",
            },
        )

        # Create a regular concept (not a guide term)
        cls.regular_concept = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="Regular Concept"
        )

        # Create a guide term concept
        cls.guide_concept = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="Guide Term Concept"
        )

        concept_tiles = []
        resource_x_resource_records = []

        for concept, name in [
            (cls.regular_concept, "Regular Concept"),
            (cls.guide_concept, "Guide Term Concept"),
        ]:
            # Label tile
            concept_tiles.append(
                TileModel(
                    resourceinstance=concept,
                    nodegroup_id=CONCEPT_NAME_NODEGROUP,
                    data={
                        CONCEPT_NAME_CONTENT_NODE: name,
                        CONCEPT_NAME_TYPE_NODE: prefLabel_reference_dt,
                        CONCEPT_NAME_LANGUAGE_NODE: "en",
                    },
                )
            )
            # Part of scheme
            rxr = ResourceXResource(
                from_resource=concept,
                from_resource_graph_id=CONCEPTS_GRAPH_ID,
                to_resource=cls.scheme,
                to_resource_graph_id=SCHEMES_GRAPH_ID,
                created=datetime.datetime.now(),
                modified=datetime.datetime.now(),
            )
            resource_x_resource_records.append(rxr)
            concept_tiles.append(
                TileModel(
                    resourceinstance=concept,
                    nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
                    data={
                        CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID: [
                            {
                                "resourceId": str(cls.scheme.pk),
                                "resourceXresourceId": str(rxr.pk),
                            },
                        ],
                    },
                )
            )
            # Top concept of scheme
            top_rxr = ResourceXResource(
                from_resource=concept,
                from_resource_graph_id=CONCEPTS_GRAPH_ID,
                to_resource=cls.scheme,
                to_resource_graph_id=SCHEMES_GRAPH_ID,
                created=datetime.datetime.now(),
                modified=datetime.datetime.now(),
            )
            resource_x_resource_records.append(top_rxr)
            concept_tiles.append(
                TileModel(
                    resourceinstance=concept,
                    nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
                    data={
                        TOP_CONCEPT_OF_NODE_AND_NODEGROUP: [
                            {
                                "resourceId": str(cls.scheme.pk),
                                "resourceXresourceId": str(top_rxr.pk),
                            },
                        ],
                    },
                )
            )

        ResourceXResource.objects.bulk_create(resource_x_resource_records)
        TileModel.objects.bulk_create(concept_tiles)

        # Create a concept type tile for the guide term concept
        TileModel.objects.create(
            resourceinstance=cls.guide_concept,
            nodegroup_id=CONCEPT_TYPE_NODEGROUP,
            data={
                CONCEPT_TYPE_NODE: [
                    {
                        "uri": GUIDE_TERM_URI,
                        "labels": [
                            {
                                "id": "",
                                "value": "guide term",
                                "language_id": "en",
                                "valuetype_id": "prefLabel",
                            }
                        ],
                    }
                ],
            },
        )

        # Create a concept type tile for the regular concept with a different URI
        TileModel.objects.create(
            resourceinstance=cls.regular_concept,
            nodegroup_id=CONCEPT_TYPE_NODEGROUP,
            data={
                CONCEPT_TYPE_NODE: [
                    {
                        "uri": "http://vocab.getty.edu/page/aat/999999999",
                        "labels": [
                            {
                                "id": "",
                                "value": "some other type",
                                "language_id": "en",
                                "valuetype_id": "prefLabel",
                            }
                        ],
                    }
                ],
            },
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_concept_builder_identifies_guide_terms_full_tree(self):
        """ConceptBuilder with no args identifies guide terms across full tree."""
        builder = ConceptBuilder()

        guide_id = str(self.guide_concept.pk)
        regular_id = str(self.regular_concept.pk)

        self.assertIn(guide_id, builder.guide_term_concept_ids)
        self.assertNotIn(regular_id, builder.guide_term_concept_ids)

    def test_concept_builder_identifies_guide_terms_scoped(self):
        """ConceptBuilder with include_parents identifies guide terms."""
        guide_id = str(self.guide_concept.pk)
        regular_id = str(self.regular_concept.pk)

        builder = ConceptBuilder([guide_id, regular_id], include_parents=True)

        self.assertIn(guide_id, builder.guide_term_concept_ids)
        self.assertNotIn(regular_id, builder.guide_term_concept_ids)

    def test_serialize_concept_includes_is_guide_term_true(self):
        """Serialized guide term concept has is_guide_term=True."""
        builder = ConceptBuilder()

        guide_id = str(self.guide_concept.pk)
        serialized = builder.serialize_concept(guide_id, children=False)

        self.assertIs(serialized["is_guide_term"], True)

    def test_serialize_concept_includes_is_guide_term_false(self):
        """Serialized regular concept has is_guide_term=False."""
        builder = ConceptBuilder()

        regular_id = str(self.regular_concept.pk)
        serialized = builder.serialize_concept(regular_id, children=False)

        self.assertIs(serialized["is_guide_term"], False)

    def test_full_tree_serialization_includes_guide_term_flag(self):
        """The full concept tree API returns is_guide_term for each concept."""
        response = self.client.get(reverse("api-concepts"))

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)

        scheme = result["schemes"][0]
        top_concepts = scheme["top_concepts"]

        guide_concept = None
        regular_concept = None
        for tc in top_concepts:
            if tc["labels"][0]["value"] == "Guide Term Concept":
                guide_concept = tc
            elif tc["labels"][0]["value"] == "Regular Concept":
                regular_concept = tc

        self.assertIsNotNone(guide_concept)
        self.assertIsNotNone(regular_concept)
        self.assertIs(guide_concept["is_guide_term"], True)
        self.assertIs(regular_concept["is_guide_term"], False)

    def test_search_results_include_guide_term_flag(self):
        """Search results include is_guide_term for concepts."""
        response = self.client.get(
            reverse("api-search"),
            QUERY_STRING="term=Guide Term Concept&maxEditDistance=0",
        )
        result = json.loads(response.content)

        self.assertGreaterEqual(len(result["data"]), 1)

        guide_result = None
        for item in result["data"]:
            if item["labels"][0]["value"] == "Guide Term Concept":
                guide_result = item
                break

        self.assertIsNotNone(guide_result)
        self.assertIs(guide_result["is_guide_term"], True)

    def test_concept_without_type_tile_is_not_guide_term(self):
        """A concept with no type tile should not be a guide term."""
        # Create a concept without any type tile
        concept = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="Untyped Concept"
        )

        reference = DataTypeFactory().get_instance("reference")
        label_config = {"controlledList": LABEL_LIST_ID}
        prefLabel_reference_dt = reference.transform_value_for_tile(
            "prefLabel", **label_config
        )

        TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data={
                CONCEPT_NAME_CONTENT_NODE: "Untyped Concept",
                CONCEPT_NAME_TYPE_NODE: prefLabel_reference_dt,
                CONCEPT_NAME_LANGUAGE_NODE: "en",
            },
        )
        rxr = ResourceXResource.objects.create(
            from_resource=concept,
            from_resource_graph_id=CONCEPTS_GRAPH_ID,
            to_resource=self.scheme,
            to_resource_graph_id=SCHEMES_GRAPH_ID,
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
        )
        TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
            data={
                TOP_CONCEPT_OF_NODE_AND_NODEGROUP: [
                    {
                        "resourceId": str(self.scheme.pk),
                        "resourceXresourceId": str(rxr.pk),
                    },
                ],
            },
        )

        builder = ConceptBuilder()
        concept_id = str(concept.pk)

        self.assertNotIn(concept_id, builder.guide_term_concept_ids)

        serialized = builder.serialize_concept(concept_id, children=False)
        self.assertIs(serialized["is_guide_term"], False)
