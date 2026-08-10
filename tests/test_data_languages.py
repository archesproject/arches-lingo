import csv
import io
import tarfile

from django.db import connection
from django.test import SimpleTestCase, TestCase

from arches.app.models.models import Language, ResourceInstance, TileModel

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
)
from arches_lingo.utils.data_languages import (
    LanguageTagResolver,
    add_missing_languages,
    get_missing_language_codes,
)
from arches_lingo.utils.lingo_fixtures import FIXTURE_TABLES, _copy_table_from_tar
from tests.tests import ViewTests

# these tests can be run from the command line via
# python manage.py test tests.test_data_languages --settings="tests.test_settings"


class LanguageTagResolverTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.resolver = LanguageTagResolver()

    def assertResolves(self, code, name, direction=Language.LEFT_TO_RIGHT):
        resolved = self.resolver.resolve(code)
        self.assertEqual(resolved.code, code)
        self.assertEqual(resolved.name, name)
        self.assertEqual(resolved.default_direction, direction)

    def test_langcodes_resolves_common_language_codes(self):
        self.assertResolves("nl", "Dutch")
        self.assertResolves("zh-hant", "Chinese (Traditional)")
        self.assertResolves("es-mx", "Spanish (Mexico)")

    def test_langcodes_names_codes_django_does_not_know(self):
        self.assertResolves("nci", "Classical Nahuatl")

    def test_compound_tag_uses_langcodes_display_name(self):
        self.assertResolves("zh-latn-wadegile", "Chinese (Latin)")
        self.assertResolves("grc-latn", "Ancient Greek (Latin)")

    def test_region_subtags_are_described(self):
        self.assertResolves("nci-mx", "Classical Nahuatl (Mexico)")

    def test_deprecated_subtag_resolves_to_its_replacement(self):
        self.assertResolves("iw", "Hebrew", Language.RIGHT_TO_LEFT)

    def test_iso_639_2_code_resolves_through_langcodes(self):
        self.assertResolves("ind", "Indonesian")

    def test_direction_comes_from_the_script_a_language_is_written_in(self):
        self.assertResolves("he", "Hebrew", Language.RIGHT_TO_LEFT)

    def test_direction_is_inherited_from_implicit_script(self):
        self.assertResolves("ar", "Arabic", Language.RIGHT_TO_LEFT)

    def test_explicit_script_subtag_overrides_the_language_direction(self):
        self.assertResolves("he-latn", "Hebrew (Latin)", Language.LEFT_TO_RIGHT)


class MissingLanguageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ViewTests.load_controlled_lists()
        ViewTests.load_ontology()
        ViewTests.load_graphs()

        concept = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="Concept with unregistered languages"
        )
        for language_code in ("en", "nci", "zh-latn-wadegile"):
            TileModel.objects.create(
                resourceinstance=concept,
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                data={
                    CONCEPT_NAME_CONTENT_NODE: f"Label ({language_code})",
                    CONCEPT_NAME_LANGUAGE_NODE: language_code,
                },
            )

    def test_only_codes_without_a_row_are_reported_missing(self):
        missing_codes = get_missing_language_codes()

        self.assertIn("nci", missing_codes)
        self.assertIn("zh-latn-wadegile", missing_codes)
        # "en" is seeded from settings.LANGUAGES and so already has a row.
        self.assertNotIn("en", missing_codes)

    def test_missing_languages_are_added_with_data_scope(self):
        added = add_missing_languages()

        added_by_code = {resolved.code: resolved for resolved in added}
        self.assertEqual(added_by_code["nci"].name, "Classical Nahuatl")
        self.assertIn("zh-latn-wadegile", added_by_code)
        self.assertNotIn("en", added_by_code)

        added_row = Language.objects.get(code="zh-latn-wadegile")
        self.assertEqual(added_row.scope, Language.DATA_SCOPE)
        self.assertFalse(added_row.isdefault)
        self.assertEqual(get_missing_language_codes(), set())

    def test_dry_run_reports_without_writing(self):
        added = add_missing_languages(dry_run=True)

        self.assertIn("nci", {resolved.code for resolved in added})
        self.assertFalse(Language.objects.filter(code="nci").exists())

    def test_i18n_string_keys_count_as_languages_in_use(self):
        concept = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="Concept with a translated label"
        )
        TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data={
                CONCEPT_NAME_CONTENT_NODE: {
                    "nl": {"value": "Label", "direction": "ltr"}
                },
                CONCEPT_NAME_LANGUAGE_NODE: "nl",
            },
        )

        self.assertIn("nl", get_missing_language_codes())


class LanguageFixtureMergeTests(TestCase):
    """The languages table is merged into the target install's own rows rather
    than restored verbatim, which is the one place this fixture format departs
    from a straight COPY."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.language_table = next(
            table for table in FIXTURE_TABLES if table.model is Language
        )

    def build_archive(self, rows, columns=None):
        columns = columns or self.language_table.columns
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(columns)
        writer.writerows(rows)
        encoded_csv = csv_buffer.getvalue().encode("utf-8")

        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            tar_info = tarfile.TarInfo(name=f"db/{self.language_table.name}.csv")
            tar_info.size = len(encoded_csv)
            tar.addfile(tar_info, io.BytesIO(encoded_csv))
        tar_buffer.seek(0)
        return tarfile.open(fileobj=tar_buffer, mode="r")

    def load_rows(self, rows, columns=None):
        tar = self.build_archive(rows, columns)
        with connection.cursor() as cursor:
            return _copy_table_from_tar(cursor, tar, self.language_table)

    def test_archive_excludes_the_id_and_default_language_columns(self):
        self.assertEqual(
            self.language_table.columns,
            ("code", "name", "default_direction", "scope"),
        )

    def test_new_languages_are_inserted(self):
        inserted_count = self.load_rows(
            [("nci", "Classical Nahuatl", Language.LEFT_TO_RIGHT, Language.DATA_SCOPE)]
        )

        self.assertEqual(inserted_count, 1)
        added = Language.objects.get(code="nci")
        self.assertEqual(added.name, "Classical Nahuatl")
        self.assertEqual(added.scope, Language.DATA_SCOPE)
        self.assertFalse(added.isdefault)

    def test_languages_the_install_already_has_are_left_alone(self):
        existing_english = Language.objects.get(code="en")

        inserted_count = self.load_rows(
            [
                ("en", "Renamed English", Language.RIGHT_TO_LEFT, Language.DATA_SCOPE),
                (
                    "nci",
                    "Classical Nahuatl",
                    Language.LEFT_TO_RIGHT,
                    Language.DATA_SCOPE,
                ),
            ]
        )

        self.assertEqual(inserted_count, 1)
        existing_english.refresh_from_db()
        self.assertEqual(existing_english.name, "English")
        self.assertTrue(existing_english.isdefault)

    def test_an_archive_without_languages_still_loads(self):
        # Archives written before languages were included have no member for
        # the table at all.
        empty_tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=empty_tar_buffer, mode="w"):
            pass
        empty_tar_buffer.seek(0)
        empty_tar = tarfile.open(fileobj=empty_tar_buffer, mode="r")

        with connection.cursor() as cursor:
            self.assertIsNone(
                _copy_table_from_tar(cursor, empty_tar, self.language_table)
            )
