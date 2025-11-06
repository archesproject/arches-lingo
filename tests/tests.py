import json
from io import BytesIO, StringIO
from http import HTTPStatus
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core import management
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import HttpRequest
from django.test import TestCase, TransactionTestCase
from django.test.utils import captured_stdout
from django.urls import reverse

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models.models import ETLModule, LoadEvent, ResourceInstance, TileModel
from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.utils.data_management.resource_graphs.importer import (
    import_graph as ResourceGraphImporter,
)

from arches_querysets.models import ResourceTileTree

from arches_lingo.etl_modules.migrate_to_lingo import LingoResourceImporter
from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    SCHEMES_GRAPH_ID,
    TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
    CLASSIFICATION_STATUS_NODEGROUP,
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_TYPE_NODE,
    SCHEME_NAME_NODEGROUP,
    SCHEME_NAME_CONTENT_NODE,
    SCHEME_NAME_LANGUAGE_NODE,
    SCHEME_NAME_TYPE_NODE,
    LANGUAGES_LIST_ID,
    LABEL_LIST_ID,
)

from .test_settings import PROJECT_TEST_ROOT

# these tests can be run from the command line via
# python manage.py test tests.tests --settings="tests.test_settings"


class ViewTests(TestCase):
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

        # Create a scheme with five concepts, each one narrower than the last,
        # and each concept after the top concept also narrower than the top.
        cls.scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Test Scheme"
        )

        reference = DataTypeFactory().get_instance("reference")
        language_config = {"controlledList": LANGUAGES_LIST_ID}
        label_config = {"controlledList": LABEL_LIST_ID}
        prefLabel_reference_dt = reference.transform_value_for_tile(
            "prefLabel", **label_config
        )
        en_reference_dt = reference.transform_value_for_tile(
            "English", **language_config
        )

        TileModel.objects.create(
            resourceinstance=cls.scheme,
            nodegroup_id=SCHEME_NAME_NODEGROUP,
            data={
                SCHEME_NAME_CONTENT_NODE: "Test Scheme",
                SCHEME_NAME_TYPE_NODE: prefLabel_reference_dt,
                SCHEME_NAME_LANGUAGE_NODE: en_reference_dt,
            },
        )

        MAX_DEPTH = 5
        CONCEPT_COUNT = 5
        cls.concepts = [
            ResourceInstance(graph_id=CONCEPTS_GRAPH_ID, name=f"Concept {num + 1}")
            for num in range(CONCEPT_COUNT)
        ]
        for concept in cls.concepts:
            concept.save()

        for i, concept in enumerate(cls.concepts):
            # Create label tile
            TileModel.objects.create(
                resourceinstance=concept,
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                data={
                    CONCEPT_NAME_CONTENT_NODE: f"Concept {i + 1}",
                    CONCEPT_NAME_TYPE_NODE: prefLabel_reference_dt,
                    CONCEPT_NAME_LANGUAGE_NODE: en_reference_dt,
                },
            )
            # Create top concept/narrower tile
            if i == 0:
                TileModel.objects.create(
                    resourceinstance=concept,
                    nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
                    data={
                        TOP_CONCEPT_OF_NODE_AND_NODEGROUP: [
                            {"resourceId": str(cls.scheme.pk)},
                        ],
                    },
                )
            elif i < MAX_DEPTH:
                TileModel.objects.create(
                    resourceinstance=concept,
                    nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
                    data={
                        CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID: [
                            # Previous concept
                            {"resourceId": str(cls.concepts[i - 1].pk)},
                            # Also add top concept
                            {"resourceId": str(cls.concepts[0].pk)},
                        ],
                    },
                )
            else:
                TileModel.objects.create(
                    resourceinstance=concept,
                    nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
                    data={
                        CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID: [
                            # Top concept only
                            {"resourceId": str(cls.concepts[0].pk)},
                        ],
                    },
                )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_get_concept_trees(self):
        with self.assertNumQueries(6):
            # 1: session
            # 2: auth
            # 3: select broader tiles, subquery for labels
            # 4: select top concept tiles, subquery for labels
            # 5: select schemes, subquery for labels
            # 6: languages
            response = self.client.get(reverse("api-concepts"))

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        scheme = result["schemes"][0]

        self.assertEqual(scheme["labels"][0]["value"], "Test Scheme")
        self.assertEqual(scheme["labels"][0]["valuetype_id"], "prefLabel")
        self.assertEqual(len(scheme["top_concepts"]), 1)
        top = scheme["top_concepts"][0]
        self.assertEqual(top["labels"][0]["value"], "Concept 1")
        self.assertEqual(len(top["narrower"]), 4)
        self.assertEqual(
            {n["labels"][0]["value"] for n in top["narrower"]},
            {"Concept 2", "Concept 3", "Concept 4", "Concept 5"},
        )
        concept_2 = [
            c for c in top["narrower"] if c["labels"][0]["value"] == "Concept 2"
        ][0]
        self.assertEqual(
            {n["labels"][0]["value"] for n in concept_2["narrower"]},
            {"Concept 3"},
        )
        self.assertEqual(
            {n["labels"][0]["valuetype_id"] for n in concept_2["narrower"]},
            {"prefLabel"},
        )

    def test_search(self):
        cases = (
            # Fuzzy match: finds all 5 concepts
            ["term=Concept 1", 5],
            ["term=Concept 1&maxEditDistance=0", 1],
            ["term=Concept 1&exact=true", 1],
            ["term=Concept 0&exact=true", 0],
            ["term=Concept 1&items=4", 4],
            ["term=Concept 1&items=4&page=2", 1],
            # Containment
            ["term=Con", 5],
            ["term=Con&maxEditDistance=0", 5],
            ["term=Con&exact=True", 0],
        )
        for query, expected_result_count in cases:
            with self.subTest(query=query):
                response = self.client.get(reverse("api-search"), QUERY_STRING=query)
                result = json.loads(response.content)
                self.assertEqual(len(result["data"]), expected_result_count, result)

    def test_lineage(self):
        # Supplement the test data with a tile that makes Concept 5
        # also a top concept of the scheme (in addition to Concept 1).
        TileModel.objects.create(
            resourceinstance=self.concepts[4],
            nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
            data={
                TOP_CONCEPT_OF_NODE_AND_NODEGROUP: [
                    {"resourceId": str(self.scheme.pk)},
                ],
            },
        )

        response = self.client.get(
            reverse("api-search"), QUERY_STRING="term=Concept 5&maxEditDistance=0"
        )
        result = json.loads(response.content)

        self.assertIs(result["data"][0]["polyhierarchical"], True)
        # Since each concept was also created with a broader concept tile for
        # the top concept (Concept 1), Concept 5 has 4 paths back to root, plus
        # another path directly to the Scheme from the extra tile created above.
        self.assertEqual(
            sorted(
                [concept["labels"][0]["value"] for concept in path]
                for path in result["data"][0]["parents"]
            ),
            [
                [
                    "Test Scheme",
                    "Concept 1",
                    "Concept 2",
                    "Concept 3",
                    "Concept 4",
                    "Concept 5",
                ],
                ["Test Scheme", "Concept 1", "Concept 3", "Concept 4", "Concept 5"],
                ["Test Scheme", "Concept 1", "Concept 4", "Concept 5"],
                ["Test Scheme", "Concept 1", "Concept 5"],
                ["Test Scheme", "Concept 5"],
            ],
        )

    def test_invalid_search_term(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(
                reverse("api-search"), QUERY_STRING="term=" + ("!" * 256)
            )
        self.assertContains(
            response,
            "Fuzzy search terms cannot exceed 255 characters.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_invalid_edit_distance(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(
                reverse("api-search"), QUERY_STRING="term=test&maxEditDistance=?"
            )
        self.assertContains(
            response,
            "Edit distance could not be converted to an integer.",
            status_code=HTTPStatus.BAD_REQUEST,
        )


class ImportTests(TransactionTestCase):

    @classmethod
    def register_lingo_resource_importer(cls):
        # management.call_command("etl_module", "register", source=str(Path(settings.APP_ROOT) / "etl_modules" / "migrate_to_lingo.py"))
        from arches.management.commands.etl_module import Command as ETLModuleCommand

        cmd = ETLModuleCommand()
        cmd.register(
            source=str(Path(settings.APP_ROOT) / "etl_modules" / "migrate_to_lingo.py")
        )

    def setUp(cls):
        """setUpClass doesn't work because the rollback fixture is applied after that."""
        ViewTests.load_ontology()
        ViewTests.load_graphs()
        cls.register_lingo_resource_importer()
        cls.moduleid = ETLModule.objects.get(slug="migrate-to-lingo").pk
        cls.admin = User.objects.get(username="admin")

    def assert_resources_loaded(self, schemes, concepts):
        self.assertEqual(schemes.count(), 1)
        self.assertEqual(concepts.count(), 16)

        # Use Junk Sculpture because it has English and German labels & statements
        junk_sculpture = concepts.filter(
            appellative_status_ascribed_name_content__any_contains="Gerümpelplastik"
        )
        self.assertEqual(junk_sculpture.count(), 1)
        junk_sculpture = junk_sculpture.first()

        # Labels
        self.assertEqual(len(junk_sculpture.aliased_data.appellative_status), 2)

        # Statements
        self.assertEqual(len(junk_sculpture.aliased_data.statement), 2)

        # Part of scheme
        scheme = junk_sculpture.aliased_data.part_of_scheme.aliased_data.part_of_scheme
        self.assertEqual(scheme.name["en"], "Test Thesaurus")

        # Hierarchical Relationship(s)
        hierarchy = junk_sculpture.aliased_data.classification_status
        self.assertEqual(len(hierarchy), 1)
        hierarchy = hierarchy[0]
        parent = hierarchy.aliased_data.classification_status_ascribed_classification
        self.assertIn(parent.name["en"], "Top Concept")

    def test_cli_import_from_skos(self):
        self.assertEqual(ResourceTileTree.get_tiles(graph_slug="scheme").count(), 0)
        self.assertEqual(ResourceTileTree.get_tiles(graph_slug="concept").count(), 0)
        stdout = StringIO()
        management.call_command(
            "packages",
            operation="import_lingo_resources",
            source=str(
                Path(PROJECT_TEST_ROOT)
                / "fixtures"
                / "data"
                / "skos_rdf_import_example.xml"
            ),
            overwrite=True,
            stdout=stdout,
        )
        schemes = ResourceTileTree.get_tiles(graph_slug="scheme")
        concepts = ResourceTileTree.get_tiles(graph_slug="concept")
        self.assert_resources_loaded(schemes, concepts)

    def test_etl_module_import_from_skos(self):
        self.assertEqual(ResourceTileTree.get_tiles(graph_slug="scheme").count(), 0)
        self.assertEqual(ResourceTileTree.get_tiles(graph_slug="concept").count(), 0)

        self.client.login(username="admin", password="admin")
        start_event = LoadEvent.objects.create(
            user_id=1, etl_module_id=self.moduleid, status="running"
        )

        request = HttpRequest()
        request.method = "POST"
        request.user = self.admin
        request.POST["load_id"] = str(start_event.loadid)
        request.POST["module"] = str(self.moduleid)
        request.POST["overwrite_option"] = "overwrite"
        request.POST["action"] = "write"

        file_name = "skos_rdf_import_example.xml"
        path = Path(PROJECT_TEST_ROOT) / "fixtures" / "data" / file_name
        with open(path, "rb") as file:
            file_data = file.read()
        inmemory_file = InMemoryUploadedFile(
            file=BytesIO(file_data),
            field_name="file",
            name=file_name,
            content_type="application/xml",
            size=len(file_data),
            charset=None,
        )
        request.FILES = {"file": inmemory_file}

        importer = LingoResourceImporter(request=request)
        write_request = importer.write(request=request)
        self.assertTrue(write_request["success"])
        schemes = ResourceTileTree.get_tiles(graph_slug="scheme")
        concepts = ResourceTileTree.get_tiles(graph_slug="concept")
        self.assert_resources_loaded(schemes, concepts)
