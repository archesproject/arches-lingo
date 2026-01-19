import json
import os
from io import BytesIO, StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core import management
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import HttpRequest
from django.test import TestCase, TransactionTestCase

from arches.app.models.models import ETLModule, LoadEvent, ResourceInstance, Value
from arches.app.utils.skos import SKOSReader
from arches_querysets.models import ResourceTileTree

from arches_lingo.etl_modules.migrate_to_lingo import LingoResourceImporter
from arches_lingo.etl_modules.lingo_resource_exporter import LingoResourceExporter
from tests.tests import ViewTests

from .test_settings import PROJECT_TEST_ROOT


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
        cls.file_name = "skos_rdf_import_example.xml"
        cls.fixture_path = Path(PROJECT_TEST_ROOT) / "fixtures" / "data" / cls.file_name

    def assert_resources_loaded(self):
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

    def test_lingo_resource_importer(self):
        """
        This test is really three tests in one, but due to trouble with TransactionTestCase
        & database rollbacks, they have to be run sequentially in one test method, relying
        on the reverse load functionality of the base importer to clean up between tests.

        There are three import paths being tested here:
        1. Management command path, importing from a SKOS RDF file.
        2. HTTP Request path, importing from a SKOS RDF file upload.
        3. Migrate Concepts & Schemes from RDM
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
        self.assert_resources_loaded()

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
        self.assert_resources_loaded()

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
        self.assert_resources_loaded()

        # No need to reverse load because tearDown will reset the DB


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
        if os.path.exists(self.file_path):
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
