import json
import os
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core import management
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import HttpRequest
from django.test import TestCase, TransactionTestCase

from arches.app.models.models import (
    DRelationType,
    ETLModule,
    LoadEvent,
    Relation,
    ResourceInstance,
    UserXNotification,
    Value,
)
from arches.app.utils.skos import SKOSReader
from arches_querysets.models import ResourceTileTree

from arches_lingo.etl_modules.migrate_to_lingo import LingoResourceImporter
from arches_lingo.etl_modules.lingo_resource_exporter import LingoResourceExporter
from tests.tests import ViewTests

from .test_settings import PROJECT_TEST_ROOT


class ImportTests(TransactionTestCase):

    @classmethod
    def register_etl_module(cls):
        from arches.management.commands.etl_module import Command as ETLModuleCommand

        etl_cmd = ETLModuleCommand()
        etl_cmd.register(
            source=str(Path(settings.APP_ROOT) / "etl_modules" / "migrate_to_lingo.py")
        )

    def setUp(cls):
        """setUpClass doesn't work because the rollback fixture is applied after that."""
        cls.register_etl_module()
        ViewTests.load_controlled_lists()
        ViewTests.load_ontology()
        ViewTests.load_graphs()
        cls.moduleid = ETLModule.objects.get(slug="migrate-to-lingo").pk
        cls.file_name = "skos_rdf_import_example.xml"
        cls.fixture_path = Path(PROJECT_TEST_ROOT) / "fixtures" / "data" / cls.file_name

    def _assert_resources_loaded(self):
        schemes = ResourceTileTree.get_tiles(graph_slug="scheme")
        concepts = ResourceTileTree.get_tiles(graph_slug="concept")
        self.assertEqual(schemes.count(), 1)
        self.assertEqual(concepts.count(), 16)

        # Use Junk Sculpture because it has English and German labels & statements
        junk_sculpture = concepts.filter(
            appellative_status_ascribed_name_content__any_contains="Gerümpelplastik"
        )
        self.assertEqual(junk_sculpture.count(), 1)
        junk_sculpture = junk_sculpture.first()

        # Labels
        label_tile_trees = junk_sculpture.aliased_data.appellative_status
        self.assertEqual(len(label_tile_trees), 2)
        # ensure default values for hidden nodes have been assigned
        self.assertIn("informational status", str(label_tile_trees[0].aliased_data))
        self.assertIn("warrant assertion event", str(label_tile_trees[0].aliased_data))

        # Statements
        statement_tile_trees = junk_sculpture.aliased_data.statement
        self.assertEqual(len(statement_tile_trees), 2)
        self.assertIn("scope note", str(statement_tile_trees[0].aliased_data))
        self.assertIn("brief texts", str(statement_tile_trees[0].aliased_data))
        self.assertIn(
            "warrant assertion event", str(statement_tile_trees[0].aliased_data)
        )

        # Type
        type_tile_tree = junk_sculpture.aliased_data.type
        self.assertIn("concept", str(type_tile_tree.aliased_data.type))
        self.assertIn("classification", str(type_tile_tree.aliased_data.type_metatype))

        # Part of scheme
        scheme = junk_sculpture.aliased_data.part_of_scheme.aliased_data.part_of_scheme
        self.assertEqual(scheme.name["en"], "Test Thesaurus")

        # Hierarchical Relationship(s)
        hierarchy = junk_sculpture.aliased_data.classification_status
        self.assertEqual(len(hierarchy), 1)
        hierarchy = hierarchy[0].aliased_data
        self.assertIn("warrant assertion event", str(hierarchy))
        parent = hierarchy.classification_status_ascribed_classification
        self.assertEqual(parent.name["en"], "Top Concept")

        # Matched Concept
        self.assertEqual(len(junk_sculpture.aliased_data.match_status), 1)

    def test_lingo_resource_importer(self):
        """
        This test is really three tests in one, but due to trouble with TransactionTestCase
        & database rollbacks, they have to be run sequentially in one test method, relying
        on the reverse load functionality of the base importer to clean up between tests.

        There are three import paths being tested here:
        1. Management command path, importing from a SKOS RDF file.
        2. HTTP Request path, importing from a SKOS RDF file upload.
        3. Migrate Concepts & Schemes from RDM
        4. Ensure that an import failure sends a notification to the user
        """

        # 1. Test Import from SKOS via management command path
        self.assertEqual(ResourceTileTree.get_tiles(graph_slug="scheme").count(), 0)
        self.assertEqual(ResourceTileTree.get_tiles(graph_slug="concept").count(), 0)
        self.assertEqual(LoadEvent.objects.count(), 0)
        stdout = StringIO()
        management.call_command(
            "packages",
            operation="import_lingo_resources",
            source=str(self.fixture_path),
            overwrite=True,
            stdout=stdout,
        )
        self._assert_resources_loaded()
        print("Test import from CLI completed.\n")

        # Reverse load to clear out the loaded resources
        loadid = LoadEvent.objects.first().loadid
        importer = LingoResourceImporter(load_id=loadid, userid=1)
        importer.reverse_load(loadid=loadid)

        # Confirm resources have been removed before moving on to next test
        self.assertEqual(ResourceTileTree.get_tiles(graph_slug="scheme").count(), 0)
        self.assertEqual(ResourceTileTree.get_tiles(graph_slug="concept").count(), 0)

        # 2. Test Import from SKOS via HTTP Request path
        self.client.login(username="admin", password="admin")
        start_event0 = LoadEvent.objects.create(
            user_id=1, etl_module_id=self.moduleid, status="running"
        )
        request0 = HttpRequest()
        request0.method = "POST"
        request0.user = User.objects.get(username="admin")
        request0.POST["load_id"] = str(start_event0.loadid)
        request0.POST["module"] = str(self.moduleid)
        request0.POST["overwrite_option"] = "overwrite"
        request0.POST["action"] = "write"

        with open(self.fixture_path, "rb") as file:
            file_data = file.read()
        inmemory_file = InMemoryUploadedFile(
            file=BytesIO(file_data),
            field_name="file",
            name=self.file_name,
            content_type="application/xml",
            size=len(file_data),
            charset=None,
        )
        request0.FILES = {"file": inmemory_file}

        importer = LingoResourceImporter(request=request0)
        write_request0 = importer.write(request=request0)
        self.assertTrue(write_request0["success"])
        self._assert_resources_loaded()
        print("Test import from Lingo UI completed.\n")

        # Reverse load to clear out the loaded resources
        importer.reverse_load(loadid=start_event0.loadid)

        # Confirm resources have been removed before moving on to next test
        self.assertEqual(ResourceTileTree.get_tiles(graph_slug="scheme").count(), 0)
        self.assertEqual(ResourceTileTree.get_tiles(graph_slug="concept").count(), 0)

        # 3. Test Migrate Concepts & Schemes from RDM
        skos = SKOSReader()
        rdf = skos.read_file(str(self.fixture_path))
        skos.save_concepts_from_skos(rdf)
        test_scheme = Value.objects.get(value="Test Thesaurus")

        # 3a. mock matched concept relation because skos import doesn't create it
        related_match = DRelationType.objects.get(relationtype="relatedMatch")
        junk_sculpture = Value.objects.get(value="junk sculpture").concept
        example_concept_1 = Value.objects.get(value="Example Concept 1").concept
        Relation(
            conceptfrom=junk_sculpture,
            conceptto=example_concept_1,
            relationtype=related_match,
        ).save()

        start_event1 = LoadEvent.objects.create(
            user_id=1, etl_module_id=self.moduleid, status="running"
        )
        request1 = HttpRequest()
        request1.method = "POST"
        request1.user = User.objects.get(username="admin")
        request1.POST["load_id"] = str(start_event1.loadid)
        request1.POST["module"] = str(self.moduleid)
        request1.POST["overwrite_option"] = "overwrite"
        request1.POST["action"] = "write"
        request1.POST["scheme"] = str(test_scheme.concept_id)

        importer = LingoResourceImporter(request=request1)
        write_request1 = importer.write(request=request1)
        self.assertTrue(write_request1["success"])
        self._assert_resources_loaded()
        print("Test migrate from RDM completed.\n")
        importer.reverse_load(loadid=start_event1.loadid)

        # 4. test_import_failure_sends_notification(self):
        admin_user = User.objects.get(username="admin")

        load_event = LoadEvent.objects.create(
            user_id=1, etl_module_id=self.moduleid, status="running"
        )
        request = HttpRequest()
        request.method = "POST"
        request.user = admin_user
        request.POST["load_id"] = str(load_event.loadid)
        request.POST["module"] = str(self.moduleid)
        request.POST["overwrite_option"] = "overwrite"
        request.POST["action"] = "write"
        # No file or scheme provided — triggers the return_with_error path

        importer = LingoResourceImporter(request=request)
        response = importer.write(request=request)

        self.assertFalse(response["success"])
        latest_notification = (
            UserXNotification.objects.filter(recipient=admin_user)
            .order_by("-notif__created")
            .first()
            .notif
        )
        self.assertIn("Import failed", latest_notification.message)


class ExportTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        ViewTests.setUpTestData()
        cls.register_lingo_resource_exporter()
        cls.moduleid = ETLModule.objects.get(slug="export-lingo-resources").pk
        cls.test_scheme = ResourceInstance.objects.get(name="Test Scheme")
        cls.test_concept = ResourceInstance.objects.get(name="Concept 1")
        cls.tempfile_dir = os.path.join(PROJECT_TEST_ROOT, "data/archestemp")

    @classmethod
    def register_lingo_resource_exporter(cls):
        from arches.management.commands.etl_module import Command as ETLModuleCommand

        cmd = ETLModuleCommand()
        cmd.register(
            source=str(
                Path(settings.APP_ROOT) / "etl_modules" / "lingo_resource_exporter.py"
            )
        )

    def tearDown(self):
        if hasattr(self, "file_path") and os.path.exists(self.file_path):
            os.remove(self.file_path)
        return super().tearDown()

    def test_export_full_hierarchy_to_skos(self):
        self.client.login(username="admin", password="admin")
        request = HttpRequest()
        request.method = "POST"
        request.user = User.objects.get(username="admin")
        request.POST["module"] = str(self.moduleid)
        request.POST["action"] = "start"
        request.POST["resourceid"] = str(self.test_scheme.pk)
        request.POST["format"] = "xml"

        exporter = LingoResourceExporter(request=request)
        response = exporter.start(request=request)
        self.assertTrue(response["success"])
        load_details = json.loads(json.loads(response["data"]["load_details"]))
        self.assertIn("scheme_name", load_details)
        file_details = load_details["file"]
        self.assertIn("name", file_details)
        self.assertIn("fileid", file_details)
        self.file_path = os.path.join(self.tempfile_dir, file_details["name"])
        self.assertTrue(os.path.exists(self.file_path))

    def test_export_partial_hierarchy_to_skos(self):
        self.client.login(username="admin", password="admin")
        request = HttpRequest()
        request.method = "POST"
        request.user = User.objects.get(username="admin")
        request.POST["module"] = str(self.moduleid)
        request.POST["action"] = "start"
        request.POST["resourceid"] = str(self.test_concept.pk)
        request.POST["format"] = "xml"
        request.POST["export_option"] = "partial"

        exporter = LingoResourceExporter(request=request)
        response = exporter.start(request=request)
        self.assertTrue(response["success"])
        load_details = json.loads(json.loads(response["data"]["load_details"]))
        self.assertIn("scheme_name", load_details)
        file_details = load_details["file"]
        self.assertIn("name", file_details)
        self.assertIn("fileid", file_details)
        self.file_path = os.path.join(self.tempfile_dir, file_details["name"])
        self.assertTrue(os.path.exists(self.file_path))

    def _run_export(self, resourceid, format, export_option=None):
        """Helper that builds a request, runs the export, and returns the response."""
        self.client.login(username="admin", password="admin")
        request = HttpRequest()
        request.method = "POST"
        request.user = User.objects.get(username="admin")
        request.POST["module"] = str(self.moduleid)
        request.POST["action"] = "start"
        request.POST["resourceid"] = str(resourceid)
        request.POST["format"] = format
        if export_option:
            request.POST["export_option"] = export_option

        exporter = LingoResourceExporter(request=request)
        return exporter.start(request=request)

    def _assert_successful_export(self, response):
        """Assert that an export response is successful and a file was produced."""
        self.assertTrue(response["success"])
        load_details = json.loads(json.loads(response["data"]["load_details"]))
        self.assertIn("scheme_name", load_details)
        file_details = load_details["file"]
        self.assertIn("name", file_details)
        self.assertIn("fileid", file_details)
        self.file_path = os.path.join(self.tempfile_dir, file_details["name"])
        self.assertTrue(os.path.exists(self.file_path))
        return file_details

    # --- RDF/XML ---

    def test_export_full_hierarchy_to_rdf(self):
        response = self._run_export(self.test_scheme.pk, "rdf")
        file_details = self._assert_successful_export(response)
        self.assertTrue(file_details["name"].endswith(".zip"))

    def test_export_partial_hierarchy_to_rdf(self):
        response = self._run_export(
            self.test_concept.pk, "rdf", export_option="partial"
        )
        file_details = self._assert_successful_export(response)
        self.assertTrue(file_details["name"].endswith(".zip"))

    # --- CSV ---

    def test_export_full_hierarchy_to_csv(self):
        response = self._run_export(self.test_scheme.pk, "csv")
        file_details = self._assert_successful_export(response)
        self.assertTrue(file_details["name"].endswith(".zip"))

    def test_export_partial_hierarchy_to_csv(self):
        response = self._run_export(
            self.test_concept.pk, "csv", export_option="partial"
        )
        file_details = self._assert_successful_export(response)
        self.assertTrue(file_details["name"].endswith(".zip"))

    # --- JSON-LD ---

    @patch(
        "arches_lingo.etl_modules.lingo_resource_exporter.JsonLdWriter.build_json",
        return_value={"@context": "mock", "@graph": []},
    )
    def test_export_full_hierarchy_to_jsonld(self, mock_build):
        response = self._run_export(self.test_scheme.pk, "jsonld")
        file_details = self._assert_successful_export(response)
        self.assertTrue(file_details["name"].endswith(".zip"))
        self.assertTrue(mock_build.called)

    @patch(
        "arches_lingo.etl_modules.lingo_resource_exporter.JsonLdWriter.build_json",
        return_value={"@context": "mock", "@graph": []},
    )
    def test_export_partial_hierarchy_to_jsonld(self, mock_build):
        response = self._run_export(
            self.test_concept.pk, "jsonld", export_option="partial"
        )
        file_details = self._assert_successful_export(response)
        self.assertTrue(file_details["name"].endswith(".zip"))
        self.assertTrue(mock_build.called)

    # --- Error handling ---

    def test_export_unsupported_format(self):
        response = self._run_export(self.test_scheme.pk, "unsupported_format")
        self.assertFalse(response["success"])

    def test_export_failure_sends_notification(self):
        admin_user = User.objects.get(username="admin")
        notifications_before = UserXNotification.objects.filter(
            recipient=admin_user
        ).count()

        response = self._run_export(self.test_scheme.pk, "unsupported_format")

        self.assertFalse(response["success"])
        notifications_after = UserXNotification.objects.filter(
            recipient=admin_user
        ).count()
        self.assertGreater(notifications_after, notifications_before)
