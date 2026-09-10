"""Tests for the AAT load's orchestration and smaller utilities.

test_aat_load.py covers the Getty export -> SKOS conversion. This module covers
utilities that sit around that conversion but are not reached by a plain SKOS
import: language repair, resource-id pinning, scheme partitioning, the
`load_aat` management command's argument mapping, and `pipeline.load_aat`'s
own step sequencing (with every step mocked -- see PipelineOrchestrationTests
for why a real end-to-end run is not exercised here).
"""

import os
import tempfile
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from arches.app.models.models import Language, ResourceInstance, TileModel

from arches_lingo import const
from arches_lingo.management.commands.load_aat_sources import (
    Command as LoadAatSourcesCommand,
    _make_resource_instance_list_value,
)
from arches_lingo.utils.aat import pipeline
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
