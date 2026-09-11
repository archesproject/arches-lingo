"""Tests for the AAT load's orchestration and smaller utilities.

test_aat_load.py covers the Getty export -> SKOS conversion. This module covers
utilities that sit around that conversion but are not reached by a plain SKOS
import: language repair, resource-id pinning, scheme partitioning, the
`load_aat` management command's argument mapping, and `pipeline.load_aat`'s
own step sequencing (with every step mocked -- see PipelineOrchestrationTests
for why a real end-to-end run is not exercised here).
"""

import datetime
import json
import os
import tempfile
from xml.sax.saxutils import escape
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.test.utils import captured_stdout

from arches.app.models.models import (
    Language,
    ResourceInstance,
    ResourceXResource,
    TileModel,
)
from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.utils.data_management.resource_graphs.importer import (
    import_graph as ResourceGraphImporter,
)

from arches_controlled_lists.models import ListItem

from arches_lingo import const
from arches_lingo.management.commands.load_aat_sources import (
    Command as LoadAatSourcesCommand,
    GROUP_GRAPH_ID,
    TEXTUAL_WORK_GRAPH_ID,
    TEXTUAL_WORK_NAME_CONTENT_NODE,
    TEXTUAL_WORK_NAME_NODEGROUP,
    _make_resource_instance_list_value,
)
from arches_lingo.management.commands.update_aat_concept_types import (
    classify_aat_concept,
    parse_aat_concept_types,
)
from arches_lingo.models import SchemeAttribution
from arches_lingo.utils.aat import pipeline
from arches_lingo.utils.aat.attribution_statement import (
    build_aat_attribution,
    set_scheme_attribution,
)
from arches_lingo.utils.aat.deferred_indexing import recalculate_descriptors_for_graph
from arches_lingo.utils.aat.progress import (
    iterate_with_progress,
    stream_lines_with_progress,
)
from arches_lingo.utils.aat.languages import (
    ensure_languages,
    repair_colliding_language_names,
)
from arches_lingo.utils.aat.resource_id_pinning import (
    snapshot_resource_ids_by_uri,
    write_resource_id_snapshot,
)
from arches_lingo.utils.aat.scheme_partition import (
    purge_scheme_partition,
    summarize_scheme_partition,
)
from arches_lingo.utils.aat.skos_conversion import AATConversionError
from arches_lingo.utils.concept_lifecycle import EDITING_STATE_ID

from tests.tests import ViewTests


def register_migrate_to_lingo_etl_module():
    """The attribution phases look their ETLModule row up by slug."""
    from arches.management.commands.etl_module import Command as ETLModuleCommand

    ETLModuleCommand().register(
        source=str(Path(settings.APP_ROOT) / "etl_modules" / "migrate_to_lingo.py")
    )


class LanguageRepairTests(TestCase):
    """`ensure_languages`/`repair_colliding_language_names` write real rows;
    the AAT-shaped test data in test_aat_load.py only exercises the pure
    `resolve_language_metadata` lookup they are built on."""

    def _write_skos_with_lang_attrs(self, *codes):
        file_descriptor, path = tempfile.mkstemp(suffix=".xml")
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as xml_file:
            for code in codes:
                xml_file.write(f'<x xml:lang="{code}">v</x>\n')
        self.addCleanup(os.remove, path)
        return path

    def test_ensure_languages_creates_missing_codes_only(self):
        Language.objects.filter(code__in=["fr-test", "ar-Latn"]).delete()
        Language.objects.create(
            code="fr-test",
            name="French (test)",
            default_direction="ltr",
            scope=Language.DATA_SCOPE,
            isdefault=False,
        )
        skos_path = self._write_skos_with_lang_attrs("fr-test", "ar-Latn")

        created = ensure_languages(skos_path, log=lambda message: None)

        created_codes = {language.code for language in created}
        self.assertIn("ar-Latn", created_codes)
        self.assertNotIn("fr-test", created_codes)  # already present
        self.assertTrue(Language.objects.filter(code="ar-Latn").exists())

    def test_ensure_languages_dry_run_creates_nothing(self):
        Language.objects.filter(code="ko-hang").delete()
        skos_path = self._write_skos_with_lang_attrs("ko-Hang")

        ensure_languages(skos_path, dry_run=True, log=lambda message: None)

        self.assertFalse(Language.objects.filter(code="ko-Hang").exists())

    def test_repair_renames_only_the_more_specific_collision(self):
        Language.objects.filter(code__in=["ko", "ko-hang-test"]).delete()
        base_language = Language.objects.create(
            code="ko",
            name="Korean (test)",
            default_direction="ltr",
            scope=Language.DATA_SCOPE,
            isdefault=False,
        )
        variant_language = Language.objects.create(
            code="ko-hang-test",
            name="Korean (test)",
            default_direction="ltr",
            scope=Language.DATA_SCOPE,
            isdefault=False,
        )

        renamed = repair_colliding_language_names(log=lambda message: None)

        base_language.refresh_from_db()
        variant_language.refresh_from_db()
        self.assertEqual(base_language.name, "Korean (test)")
        self.assertNotEqual(variant_language.name, "Korean (test)")
        self.assertIn(variant_language, renamed)


class ResourceIdPinningAndPartitionTests(TestCase):
    """Reuses the scheme + narrower-concept chain ViewTests already builds."""

    @classmethod
    def setUpTestData(cls):
        ViewTests.load_controlled_lists()
        ViewTests.load_ontology()
        ViewTests.load_graphs()
        cls.admin = User.objects.get(username="admin")

    def setUp(self):
        # Build the same five-concept scheme ViewTests.setUpTestData builds,
        # without depending on its class-scoped fixtures directly.
        self.scheme = ResourceInstance.objects.create(
            graph_id=const.SCHEMES_GRAPH_ID, name="Pinning Test Scheme"
        )
        top_concept = ResourceInstance.objects.create(
            graph_id=const.CONCEPTS_GRAPH_ID, name="Top Concept"
        )
        TileModel(
            resourceinstance=top_concept,
            nodegroup_id=const.CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
            data={
                const.CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID: [
                    {
                        "resourceId": str(self.scheme.pk),
                        "ontologyProperty": const.TOP_CONCEPT_OF_ONTOLOGY_PROPERTY,
                        "inverseOntologyProperty": "",
                        "resourceXresourceId": "",
                    }
                ]
            },
        ).save()
        self.top_concept = top_concept

    def test_snapshot_matches_only_the_given_prefix(self):
        TileModel(
            resourceinstance=self.top_concept,
            nodegroup_id=const.URI_NODEGROUP,
            data={const.URI_CONTENT_NODE: "http://vocab.getty.edu/aat/300000001"},
        ).save()

        snapshot = snapshot_resource_ids_by_uri("http://vocab.getty.edu/aat/")

        self.assertEqual(
            snapshot["http://vocab.getty.edu/aat/300000001"], self.top_concept.pk
        )

    def test_write_resource_id_snapshot_pins_the_scheme_uri(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = os.path.join(temp_dir, "snapshot.csv")

            row_count = write_resource_id_snapshot(
                "http://vocab.getty.edu/aat/",
                csv_path,
                scheme_resource_id=self.scheme.pk,
            )

            with open(csv_path, encoding="utf-8") as csv_file:
                contents = csv_file.read()

        self.assertEqual(row_count, 1)
        self.assertIn(f"http://vocab.getty.edu/aat/,{self.scheme.pk}", contents)

    def test_summarize_reports_the_concept_alone(self):
        summary = summarize_scheme_partition(self.scheme.pk)
        self.assertEqual(summary.get("Concept"), 1)

    def test_purge_removes_the_concept_but_keeps_the_scheme(self):
        purge_scheme_partition(self.scheme.pk, log=lambda message: None)

        self.assertFalse(
            ResourceInstance.objects.filter(pk=self.top_concept.pk).exists()
        )
        self.assertTrue(ResourceInstance.objects.filter(pk=self.scheme.pk).exists())


class LoadAatCommandTests(TestCase):
    """The command is a thin argument-mapping layer over `pipeline.load_aat`."""

    @patch("arches_lingo.management.commands.load_aat.load_aat")
    def test_options_are_translated_into_pipeline_arguments(self, mock_load_aat):
        mock_load_aat.return_value = {
            "concepts": 5,
            "scheme_id": "11111111-1111-1111-1111-111111111111",
            "extraction_date": None,
        }

        call_command(
            "load_aat",
            working_directory="/tmp/aat-test",
            keep_existing=True,
            new_resource_ids=True,
            lifecycle_state="editing",
            index=True,
            no_progress=True,
            stdout=StringIO(),
        )

        _, call_kwargs = mock_load_aat.call_args
        self.assertEqual(call_kwargs["replace_existing"], False)
        self.assertEqual(call_kwargs["preserve_resource_ids"], False)
        self.assertEqual(call_kwargs["skip_indexing"], False)
        self.assertEqual(call_kwargs["show_progress"], False)
        self.assertEqual(call_kwargs["lifecycle_state_id"], EDITING_STATE_ID)

    @patch("arches_lingo.management.commands.load_aat.load_aat")
    def test_conversion_error_becomes_a_command_error(self, mock_load_aat):
        mock_load_aat.side_effect = AATConversionError("bad archive")

        with self.assertRaises(CommandError):
            call_command(
                "load_aat", working_directory="/tmp/aat-test", stdout=StringIO()
            )


class LoadAatSourcesHelperTests(TestCase):
    """Unit tests for load_aat_sources.py's smaller building blocks, which the
    dry-run smoke test in test_aat_load.py does not reach."""

    @classmethod
    def setUpTestData(cls):
        ViewTests.load_controlled_lists()
        ViewTests.load_ontology()
        ViewTests.load_graphs()

    def test_resource_instance_list_value_carries_a_cross_reference_id(self):
        resource_id = "11111111-1111-1111-1111-111111111111"

        value = _make_resource_instance_list_value([resource_id])

        self.assertEqual(value[0]["resourceId"], resource_id)
        self.assertEqual(value[0]["ontologyProperty"], "")

    def test_label_key_normalizes_case_and_whitespace(self):
        command = LoadAatSourcesCommand()

        key = command._make_label_key("  Trumpets  ", "EN")

        self.assertEqual(key, "Trumpets||en")

    def test_note_key_truncates_long_content(self):
        command = LoadAatSourcesCommand()

        key = command._make_note_key("x" * 300, "en")

        self.assertEqual(key, f"{'x' * 200}||en")

    def test_blank_tile_has_an_entry_per_node_in_the_nodegroup(self):
        command = LoadAatSourcesCommand()

        blank_tile = command._get_blank_tile(const.CONCEPT_NAME_NODEGROUP)

        self.assertIn(const.CONCEPT_NAME_CONTENT_NODE, blank_tile)
        self.assertIsNone(blank_tile[const.CONCEPT_NAME_CONTENT_NODE]["value"])

    def test_default_lifecycle_state_is_none_for_an_unknown_graph(self):
        command = LoadAatSourcesCommand()

        state = command._get_default_lifecycle_state(
            "00000000-0000-0000-0000-000000000000"
        )

        self.assertIsNone(state)


class PipelineOrchestrationTests(SimpleTestCase):
    """Exercises `load_aat`'s step sequencing and reload branching with every
    step mocked, so the DB-heavy steps stay covered by their own unit tests
    while this covers only the orchestration logic layered over them."""

    def _patch_steps(self, existing_scheme_id=None):
        patches = {
            "download_archive": patch.object(pipeline, "download_archive"),
            "read_archive_extraction_date": patch.object(
                pipeline, "read_archive_extraction_date", return_value=None
            ),
            "convert_archive_to_skos": patch.object(
                pipeline, "convert_archive_to_skos", return_value=3
            ),
            "extract_attribution_from_archive": patch.object(
                pipeline, "extract_attribution_from_archive"
            ),
            "ensure_languages": patch.object(pipeline, "ensure_languages"),
            "repair_colliding_language_names": patch.object(
                pipeline, "repair_colliding_language_names"
            ),
            "find_existing_aat_scheme_id": patch.object(
                pipeline,
                "find_existing_aat_scheme_id",
                side_effect=[existing_scheme_id, "new-scheme-id"],
            ),
            "write_resource_id_snapshot": patch.object(
                pipeline, "write_resource_id_snapshot", return_value=0
            ),
            "summarize_scheme_partition": patch.object(
                pipeline, "summarize_scheme_partition", return_value={}
            ),
            "purge_scheme_partition": patch.object(pipeline, "purge_scheme_partition"),
            "call_command": patch.object(pipeline, "call_command"),
            "remove_orphaned_aat_schemes": patch.object(
                pipeline, "remove_orphaned_aat_schemes"
            ),
            "set_scheme_attribution": patch.object(pipeline, "set_scheme_attribution"),
        }
        mocks = {name: entered.start() for name, entered in patches.items()}
        for entered in patches.values():
            self.addCleanup(entered.stop)
        return mocks

    def test_fresh_load_skips_the_reload_steps(self):
        mocks = self._patch_steps(existing_scheme_id=None)

        result = pipeline.load_aat(
            "/tmp/aat-test",
            archive_path="/tmp/aat-test/explicit.zip",
            log=lambda m: None,
        )

        mocks["write_resource_id_snapshot"].assert_not_called()
        mocks["purge_scheme_partition"].assert_not_called()
        mocks["remove_orphaned_aat_schemes"].assert_called_once()
        self.assertEqual(
            mocks["remove_orphaned_aat_schemes"].call_args.args[0], "new-scheme-id"
        )
        self.assertEqual(mocks["call_command"].call_count, 3)
        self.assertEqual(result["concepts"], 3)
        self.assertEqual(result["scheme_id"], "new-scheme-id")

    def test_reload_pins_ids_and_purges_the_previous_scheme(self):
        mocks = self._patch_steps(existing_scheme_id="old-scheme-id")

        pipeline.load_aat(
            "/tmp/aat-test",
            archive_path="/tmp/aat-test/explicit.zip",
            replace_existing=True,
            preserve_resource_ids=True,
            log=lambda m: None,
        )

        mocks["write_resource_id_snapshot"].assert_called_once()
        mocks["purge_scheme_partition"].assert_called_once()
        self.assertEqual(
            mocks["purge_scheme_partition"].call_args.args[0], "old-scheme-id"
        )

    def test_reload_without_replace_or_pin_leaves_the_previous_scheme_alone(self):
        mocks = self._patch_steps(existing_scheme_id="old-scheme-id")

        pipeline.load_aat(
            "/tmp/aat-test",
            archive_path="/tmp/aat-test/explicit.zip",
            replace_existing=False,
            preserve_resource_ids=False,
            log=lambda m: None,
        )

        mocks["write_resource_id_snapshot"].assert_not_called()
        mocks["purge_scheme_partition"].assert_not_called()

    def test_no_archive_path_downloads_first(self):
        mocks = self._patch_steps(existing_scheme_id=None)

        pipeline.load_aat("/tmp/aat-test", log=lambda m: None)

        mocks["download_archive"].assert_called_once()


class LoadAatSourcesEndToEndTests(TransactionTestCase):
    """Run the command's three phases against real graphs.

    LoadAatSourcesHelperTests above covers the small pieces in isolation; this
    covers what they add up to -- source and contributor resources created from
    the extracted attribution, and the references merged onto the label and
    note tiles that already exist.

    TransactionTestCase, as tests.test_import_export.ImportTests is and for the
    same reason: saving staged tiles disables and re-enables the triggers on
    `tiles`, which a wrapped test transaction will not allow.

    `serialized_rollback` restores the rows arches' migrations provide -- the
    Language table among them -- which the flush between tests would otherwise
    leave empty for everything that runs afterwards.
    """

    serialized_rollback = True

    graph_fixtures = [
        "Scheme.json",
        "Concept.json",
        "textual_work_system.json",
        "group_system.json",
    ]

    CONCEPT_URI = "http://vocab.getty.edu/aat/300000001"
    SOURCE_URI = "http://vocab.getty.edu/aat/source/2000000001"
    CONTRIBUTOR_URI = "http://vocab.getty.edu/aat/contrib/1000000001"

    def setUp(self):
        # Loaded per test, as ImportTests does: a TransactionTestCase flushes
        # between tests, so class-level setup would not survive.
        ViewTests.load_controlled_lists()
        ViewTests.load_ontology()
        graph_directory = Path(settings.APP_ROOT) / "pkg" / "graphs" / "resource_models"
        for fixture_name in self.graph_fixtures:
            with open(graph_directory / fixture_name) as graph_file:
                graph = JSONDeserializer().deserialize(graph_file)["graph"]
            with captured_stdout():
                ResourceGraphImporter(graph, overwrite_graphs=True)
        register_migrate_to_lingo_etl_module()

        self.concept = ResourceInstance.objects.create(
            graph_id=const.CONCEPTS_GRAPH_ID, name="Trumpets"
        )
        self.label_tile = TileModel.objects.create(
            resourceinstance=self.concept,
            nodegroup_id=const.CONCEPT_NAME_NODEGROUP,
            data={
                const.CONCEPT_NAME_CONTENT_NODE: "trumpets",
                const.CONCEPT_NAME_LANGUAGE_NODE: "en",
            },
        )
        self.note_tile = TileModel.objects.create(
            resourceinstance=self.concept,
            nodegroup_id=const.STATEMENT_NODEGROUP,
            data={
                const.STATEMENT_CONTENT_NODE: "Brass instruments.",
                const.STATEMENT_LANGUAGE_NODE: "en",
            },
        )

    def add_uri_tile(self):
        TileModel.objects.create(
            resourceinstance=self.concept,
            nodegroup_id=const.URI_NODEGROUP,
            data={const.URI_CONTENT_NODE: self.CONCEPT_URI},
        )

    def run_command(self):
        attribution = {
            "sources": {
                self.SOURCE_URI: {
                    "title": "A Source, second edition (1999)",
                    "short_title": "A Source (1999)",
                }
            },
            "contributors": {
                self.CONTRIBUTOR_URI: {"name": "Example Contributor", "nick": "EX"}
            },
            "labels": {
                self.CONCEPT_URI: [
                    {
                        "literal_form": "trumpets",
                        "language": "en",
                        "label_type": "prefLabel",
                        "sources": [self.SOURCE_URI],
                        "contributors": [self.CONTRIBUTOR_URI],
                    }
                ]
            },
            "notes": {
                self.CONCEPT_URI: [
                    {
                        "value": "Brass instruments.",
                        "language": "en",
                        "sources": [self.SOURCE_URI],
                        "contributors": [self.CONTRIBUTOR_URI],
                    }
                ]
            },
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            attribution_path = os.path.join(temporary_directory, "attribution.json")
            with open(attribution_path, "w", encoding="utf-8") as attribution_file:
                json.dump(attribution, attribution_file)
            captured_output = StringIO()
            call_command(
                "load_aat_sources",
                source=attribution_path,
                skip_indexing=True,
                no_progress=True,
                stdout=captured_output,
            )
        return captured_output.getvalue()

    def test_sources_and_contributors_become_resources_and_reach_the_tiles(self):
        self.add_uri_tile()

        self.run_command()

        source_resource = ResourceInstance.objects.get(graph_id=TEXTUAL_WORK_GRAPH_ID)
        contributor_resource = ResourceInstance.objects.get(graph_id=GROUP_GRAPH_ID)

        self.label_tile.refresh_from_db()
        self.note_tile.refresh_from_db()
        for tile, source_node, actor_node in (
            (
                self.label_tile,
                const.CONCEPT_NAME_DATA_ASSIGNMENT_OBJ_USED_NODE,
                const.CONCEPT_NAME_DATA_ASSIGNMENT_ACTOR_NODE,
            ),
            (
                self.note_tile,
                const.STATEMENT_DATA_ASSIGNMENT_OBJ_USED_NODE,
                const.STATEMENT_DATA_ASSIGNMENT_ACTOR_NODE,
            ),
        ):
            self.assertEqual(
                tile.data[source_node][0]["resourceId"], str(source_resource.pk)
            )
            self.assertEqual(
                tile.data[actor_node][0]["resourceId"], str(contributor_resource.pk)
            )

        # The merge is responsible for the relationship rows too.
        self.assertEqual(
            ResourceXResource.objects.filter(tile_id=self.label_tile.pk).count(), 2
        )

    def test_the_short_title_names_the_source_resource(self):
        """Sources carry a long and a short title; the short one is the name."""
        self.add_uri_tile()

        self.run_command()

        source_resource = ResourceInstance.objects.get(graph_id=TEXTUAL_WORK_GRAPH_ID)
        name_tile = TileModel.objects.get(
            resourceinstance=source_resource, nodegroup_id=TEXTUAL_WORK_NAME_NODEGROUP
        )
        self.assertEqual(
            name_tile.data[TEXTUAL_WORK_NAME_CONTENT_NODE], "A Source (1999)"
        )

    def test_rerunning_reuses_the_resources_the_first_run_created(self):
        """Resource ids are derived from the source URI, so a second run must
        not create a second copy of every source and contributor."""
        self.add_uri_tile()

        self.run_command()
        output = self.run_command()

        self.assertEqual(
            ResourceInstance.objects.filter(graph_id=TEXTUAL_WORK_GRAPH_ID).count(), 1
        )
        self.assertEqual(
            ResourceInstance.objects.filter(graph_id=GROUP_GRAPH_ID).count(), 1
        )
        self.assertIn("1 already exist", output)

    def test_concepts_are_matched_by_label_when_no_uri_tile_exists(self):
        """Data loaded before URI tiles were written still has to be matched;
        the fallback then backfills the URI tile for the next run."""
        output = self.run_command()

        self.assertIn("No URI tiles found", output)
        uri_tile = TileModel.objects.get(
            resourceinstance=self.concept, nodegroup_id=const.URI_NODEGROUP
        )
        self.assertEqual(uri_tile.data[const.URI_CONTENT_NODE], self.CONCEPT_URI)
        self.label_tile.refresh_from_db()
        self.assertIn(
            const.CONCEPT_NAME_DATA_ASSIGNMENT_OBJ_USED_NODE, self.label_tile.data
        )

    def test_attribution_for_an_unknown_concept_is_reported_as_skipped(self):
        self.add_uri_tile()
        self.concept.tilemodel_set.filter(
            nodegroup_id=const.CONCEPT_NAME_NODEGROUP
        ).delete()

        output = self.run_command()

        self.assertIn("skipped", output.lower())


class UpdateAatConceptTypesTests(TestCase):
    """AAT encodes a concept's type in its English label rather than in a
    property, so the type has to be inferred after the concepts are loaded."""

    @classmethod
    def setUpTestData(cls):
        ViewTests.load_controlled_lists()
        ViewTests.load_ontology()
        ViewTests.load_graphs()

    def write_skos(self, *concept_blocks):
        skos = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"'
            ' xmlns:skos="http://www.w3.org/2004/02/skos/core#">\n'
            + "".join(concept_blocks)
            + "</rdf:RDF>\n"
        )
        file_descriptor, path = tempfile.mkstemp(suffix=".xml")
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as skos_file:
            skos_file.write(skos)
        self.addCleanup(os.remove, path)
        return path

    @staticmethod
    def concept_block(aat_number, english_label, top_concept_of=False):
        top_concept = (
            '    <skos:topConceptOf rdf:resource="http://vocab.getty.edu/aat/"/>\n'
            if top_concept_of
            else ""
        )
        return (
            f'  <skos:Concept rdf:about="http://vocab.getty.edu/aat/{aat_number}">\n'
            f'    <skos:prefLabel xml:lang="en">{escape(english_label)}'
            "</skos:prefLabel>\n"
            f"{top_concept}"
            "  </skos:Concept>\n"
        )

    def test_label_shape_decides_the_concept_type(self):
        self.assertEqual(classify_aat_concept("Objects Facet", True), "facet")
        # A facet label without topConceptOf is an ordinary concept.
        self.assertEqual(classify_aat_concept("Objects Facet", False), "concept")
        self.assertEqual(
            classify_aat_concept("<furniture by form> (hierarchy name)", False),
            "hierarchy name",
        )
        self.assertEqual(
            classify_aat_concept("<containers by form>", False), "guide term"
        )
        self.assertEqual(classify_aat_concept("trumpets", False), "concept")
        self.assertEqual(classify_aat_concept("", False), "concept")

    def test_parsing_keeps_only_the_concepts_that_are_not_plain_concepts(self):
        skos_path = self.write_skos(
            self.concept_block("300000001", "trumpets"),
            self.concept_block("300000002", "Objects Facet", top_concept_of=True),
            self.concept_block("300000003", "<containers by form>"),
        )

        type_map = parse_aat_concept_types(skos_path)

        self.assertEqual(
            type_map,
            {
                "http://vocab.getty.edu/aat/300000002": "facet",
                "http://vocab.getty.edu/aat/300000003": "guide term",
            },
        )

    def test_only_the_first_english_label_is_considered(self):
        """A concept can carry several English labels; the preferred one is
        written first, and a later alternate must not override the type."""
        skos_path = self.write_skos(
            '  <skos:Concept rdf:about="http://vocab.getty.edu/aat/300000004">\n'
            '    <skos:prefLabel xml:lang="en">&lt;boxes by form&gt;</skos:prefLabel>\n'
            '    <skos:prefLabel xml:lang="en">boxes</skos:prefLabel>\n'
            "  </skos:Concept>\n"
        )

        self.assertEqual(
            parse_aat_concept_types(skos_path),
            {"http://vocab.getty.edu/aat/300000004": "guide term"},
        )

    def test_non_english_labels_do_not_classify(self):
        skos_path = self.write_skos(
            '  <skos:Concept rdf:about="http://vocab.getty.edu/aat/300000005">\n'
            '    <skos:prefLabel xml:lang="fr">&lt;boîtes&gt;</skos:prefLabel>\n'
            "  </skos:Concept>\n"
        )

        self.assertEqual(parse_aat_concept_types(skos_path), {})

    def test_command_writes_the_type_onto_the_matching_concept(self):
        concept = ResourceInstance.objects.create(
            graph_id=const.CONCEPTS_GRAPH_ID, name="Containers guide term"
        )
        TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=const.URI_NODEGROUP,
            data={const.URI_CONTENT_NODE: "http://vocab.getty.edu/aat/300000003"},
        )
        type_tile = TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=const.CONCEPT_TYPE_NODEGROUP,
            data={const.CONCEPT_TYPE_NODEID: None},
        )
        skos_path = self.write_skos(
            self.concept_block("300000003", "<containers by form>"),
        )

        call_command("update_aat_concept_types", source=skos_path, stdout=StringIO())

        type_tile.refresh_from_db()
        self.assertEqual(
            type_tile.data[const.CONCEPT_TYPE_NODEID][0]["labels"][0]["value"],
            "guide term",
        )

    def test_dry_run_reports_without_writing(self):
        concept = ResourceInstance.objects.create(
            graph_id=const.CONCEPTS_GRAPH_ID, name="Containers guide term"
        )
        TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=const.URI_NODEGROUP,
            data={const.URI_CONTENT_NODE: "http://vocab.getty.edu/aat/300000003"},
        )
        type_tile = TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=const.CONCEPT_TYPE_NODEGROUP,
            data={const.CONCEPT_TYPE_NODEID: None},
        )
        skos_path = self.write_skos(
            self.concept_block("300000003", "<containers by form>"),
        )
        captured_output = StringIO()

        call_command(
            "update_aat_concept_types",
            source=skos_path,
            dry_run=True,
            stdout=captured_output,
        )

        type_tile.refresh_from_db()
        self.assertIsNone(type_tile.data[const.CONCEPT_TYPE_NODEID])
        self.assertIn("would update", captured_output.getvalue())

    def test_a_missing_term_types_list_is_an_actionable_error(self):
        ListItem.objects.filter(list_id=const.CONCEPT_TYPE_LIST_ID).delete()

        with self.assertRaises(CommandError) as raised:
            call_command(
                "update_aat_concept_types",
                source=self.write_skos(),
                stdout=StringIO(),
            )

        self.assertIn("term_types.xml", str(raised.exception))


class SchemeAttributionTests(TestCase):
    """The Getty licence requires the statement to be stored with the scheme."""

    @classmethod
    def setUpTestData(cls):
        ViewTests.load_controlled_lists()
        ViewTests.load_ontology()
        ViewTests.load_graphs()

    def setUp(self):
        self.scheme = ResourceInstance.objects.create(
            graph_id=const.SCHEMES_GRAPH_ID, name="Attribution Test Scheme"
        )

    def test_the_statement_is_stored_against_the_scheme(self):
        attribution_text = build_aat_attribution(datetime.date(2026, 8, 1))

        set_scheme_attribution(self.scheme.pk, attribution_text)

        stored = SchemeAttribution.objects.get(scheme=self.scheme)
        self.assertIn("August 1, 2026", stored.attribution)

    def test_reloading_replaces_the_previous_statement(self):
        set_scheme_attribution(
            self.scheme.pk, build_aat_attribution(datetime.date(2025, 1, 13))
        )
        set_scheme_attribution(
            self.scheme.pk, build_aat_attribution(datetime.date(2026, 8, 1))
        )

        self.assertEqual(
            SchemeAttribution.objects.filter(scheme=self.scheme).count(), 1
        )
        self.assertIn(
            "August 1, 2026",
            SchemeAttribution.objects.get(scheme=self.scheme).attribution,
        )


class SchemeDiscoveryTests(TestCase):
    """`load_aat` finds the scheme a previous run left behind by its Getty URI,
    and clears out schemes a failed run abandoned."""

    @classmethod
    def setUpTestData(cls):
        ViewTests.load_controlled_lists()
        ViewTests.load_ontology()
        ViewTests.load_graphs()

    def make_scheme(self, name, uri=None):
        scheme = ResourceInstance.objects.create(
            graph_id=const.SCHEMES_GRAPH_ID, name=name
        )
        if uri:
            TileModel.objects.create(
                resourceinstance=scheme,
                nodegroup_id=const.SCHEME_URI_NODEGROUP,
                data={const.SCHEME_URI_CONTENT_NODE: uri},
            )
        return scheme

    def test_the_scheme_is_found_by_its_uri_not_its_label(self):
        """The label is configurable, so a renamed scheme still has to match."""
        self.make_scheme("Some Other Vocabulary", "http://example.org/other/")
        aat_scheme = self.make_scheme(
            "Renamed By A Curator", "http://vocab.getty.edu/aat/"
        )

        self.assertEqual(pipeline.find_existing_aat_scheme_id(), aat_scheme.pk)

    def test_no_loaded_aat_scheme_is_not_an_error(self):
        self.make_scheme("Some Other Vocabulary", "http://example.org/other/")

        self.assertIsNone(pipeline.find_existing_aat_scheme_id())

    def test_an_abandoned_empty_scheme_is_removed(self):
        kept_scheme = self.make_scheme("Kept", "http://vocab.getty.edu/aat/")
        abandoned_scheme = self.make_scheme("Abandoned By A Failed Run")

        removed = pipeline.remove_orphaned_aat_schemes(
            kept_scheme.pk, log=lambda message: None
        )

        self.assertEqual(removed, [abandoned_scheme.pk])
        self.assertFalse(
            ResourceInstance.objects.filter(pk=abandoned_scheme.pk).exists()
        )
        self.assertTrue(ResourceInstance.objects.filter(pk=kept_scheme.pk).exists())

    def test_a_scheme_holding_concepts_is_left_alone(self):
        """Emptiness is the test, so a second populated scheme must survive."""
        kept_scheme = self.make_scheme("Kept", "http://vocab.getty.edu/aat/")
        other_scheme = self.make_scheme("Another Vocabulary")
        concept = ResourceInstance.objects.create(
            graph_id=const.CONCEPTS_GRAPH_ID, name="A Concept"
        )
        TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=const.CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
            data={
                const.CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID: [
                    {"resourceId": str(other_scheme.pk)}
                ]
            },
        )

        removed = pipeline.remove_orphaned_aat_schemes(
            kept_scheme.pk, log=lambda message: None
        )

        self.assertEqual(removed, [])
        self.assertTrue(ResourceInstance.objects.filter(pk=other_scheme.pk).exists())


class DescriptorRecalculationTests(TestCase):
    """Writing tiles directly bypasses the arches save path, so nothing else
    refreshes the descriptors the interface shows as a resource's name."""

    @classmethod
    def setUpTestData(cls):
        ViewTests.load_controlled_lists()
        ViewTests.load_ontology()
        ViewTests.load_graphs()

    def test_a_name_is_derived_from_the_label_tile(self):
        concept = ResourceInstance.objects.create(graph_id=const.CONCEPTS_GRAPH_ID)
        TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=const.CONCEPT_NAME_NODEGROUP,
            data={
                const.CONCEPT_NAME_CONTENT_NODE: "trumpets",
                const.CONCEPT_NAME_LANGUAGE_NODE: "en",
            },
        )

        recalculated = recalculate_descriptors_for_graph(
            const.CONCEPTS_GRAPH_ID, log=lambda message: None
        )

        concept.refresh_from_db()
        self.assertEqual(recalculated, 1)
        self.assertEqual(concept.descriptors["en"]["name"], "trumpets")


class ProgressReportingTests(SimpleTestCase):
    """The bars wrap the streaming reads, so they must not alter what is read."""

    def test_items_are_yielded_unchanged_with_the_bar_on(self):
        output_stream = StringIO()

        yielded = list(
            iterate_with_progress(
                iter(["a", "b", "c"]),
                total=3,
                title="items",
                show_progress=True,
                output_stream=output_stream,
            )
        )

        self.assertEqual(yielded, ["a", "b", "c"])
        self.assertIn("items", output_stream.getvalue())

    def test_a_step_larger_than_the_total_does_not_overrun_the_bar(self):
        """Batched loops report rows rather than batches, and the last batch is
        usually short."""
        output_stream = StringIO()

        yielded = list(
            iterate_with_progress(
                iter([["a", "b"], ["c"]]),
                total=3,
                title="rows",
                step=2,
                show_progress=True,
                output_stream=output_stream,
            )
        )

        self.assertEqual(yielded, [["a", "b"], ["c"]])

    def test_lines_are_yielded_unchanged_with_the_bar_on(self):
        output_stream = StringIO()

        yielded = list(
            stream_lines_with_progress(
                [iter([b"one\n", b"two\n"]), iter([b"three\n"])],
                total_bytes=14,
                title="bytes",
                show_progress=True,
                output_stream=output_stream,
            )
        )

        self.assertEqual(yielded, [b"one\n", b"two\n", b"three\n"])
