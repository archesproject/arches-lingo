import csv
import io
import tarfile
import tempfile

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
    SubtagRegistry,
    add_missing_languages,
    get_missing_language_codes,
)
from arches_lingo.utils.lingo_fixtures import FIXTURE_TABLES, _copy_table_from_tar
from tests.tests import ViewTests

# these tests can be run from the command line via
# python manage.py test tests.test_data_languages --settings="tests.test_settings"

# A stand-in for the IANA Language Subtag Registry, carrying only the subtags
# the resolver tests exercise. Using a fixture rather than the real registry
# keeps these tests offline and makes the expected names explicit.
SUBTAG_REGISTRY_FIXTURE = """File-Date: 2026-06-14
%%
Type: language
Subtag: ar
Description: Arabic
Suppress-Script: Arab
%%
Type: language
Subtag: acw
Description: Hijazi Arabic
Macrolanguage: ar
%%
Type: language
Subtag: he
Description: Hebrew
Suppress-Script: Hebr
%%
Type: language
Subtag: id
Description: Indonesian
Suppress-Script: Latn
%%
Type: language
Subtag: iw
Description: Hebrew
Deprecated: 1989-01-01
Preferred-Value: he
%%
Type: language
Subtag: nci
Description: Classical Nahuatl
%%
Type: language
Subtag: qaa..qtz
Description: Private use
%%
Type: language
Subtag: zh
Description: Chinese
Scope: macrolanguage
%%
Type: language
Subtag: grc
Description: Ancient Greek (to 1453)
%%
Type: extlang
Subtag: yue
Description: Yue Chinese
Preferred-Value: yue
Macrolanguage: zh
%%
Type: script
Subtag: Latn
Description: Latin
%%
Type: script
Subtag: Hebr
Description: Hebrew
%%
Type: script
Subtag: Arab
Description: Arabic
%%
Type: region
Subtag: 002
Description: Africa
%%
Type: region
Subtag: MX
Description: Mexico
%%
Type: variant
Subtag: wadegile
Description: Wade-Giles romanization
%%
Type: variant
Subtag: pinyin
Description: Pinyin romanization
"""


class SubtagRegistryTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.registry = SubtagRegistry(SUBTAG_REGISTRY_FIXTURE)

    def test_subtags_are_indexed_by_type(self):
        # "Hebrew" is both a language and a script; the type disambiguates.
        self.assertEqual(self.registry.find("language", "he").description, "Hebrew")
        self.assertEqual(self.registry.find("script", "hebr").description, "Hebrew")
        self.assertIsNone(self.registry.find("region", "he"))

    def test_subtag_lookup_is_case_insensitive(self):
        self.assertEqual(self.registry.find("script", "LATN").description, "Latin")

    def test_registered_fields_are_captured(self):
        deprecated_hebrew = self.registry.find("language", "iw")
        self.assertEqual(deprecated_hebrew.preferred_value, "he")
        self.assertEqual(self.registry.find("language", "acw").macrolanguage, "ar")
        self.assertEqual(self.registry.find("language", "ar").suppress_script, "Arab")

    def test_private_use_ranges_are_recognized_but_not_described(self):
        self.assertIsNone(self.registry.find("language", "qqq"))
        self.assertTrue(self.registry.is_private_use("language", "qqq"))
        self.assertFalse(self.registry.is_private_use("language", "nci"))


class LanguageTagResolverTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.resolver = LanguageTagResolver(SubtagRegistry(SUBTAG_REGISTRY_FIXTURE))

    def assertResolves(self, code, name, direction=Language.LEFT_TO_RIGHT):
        resolved = self.resolver.resolve(code)
        self.assertEqual(resolved.code, code)
        self.assertEqual(resolved.name, name)
        self.assertEqual(resolved.default_direction, direction)

    def test_django_language_list_names_codes_it_knows(self):
        # Matching arches' own seeding keeps names consistent with the rows
        # arches creates from settings.LANGUAGES.
        self.assertResolves("nl", "Dutch")
        self.assertResolves("zh-hant", "Traditional Chinese")
        self.assertResolves("es-mx", "Mexican Spanish")

    def test_registry_names_codes_django_does_not_know(self):
        self.assertResolves("nci", "Classical Nahuatl")

    def test_compound_tag_recombines_its_subtag_descriptions(self):
        self.assertResolves(
            "zh-latn-wadegile", "Chinese (Latin, Wade-Giles romanization)"
        )
        self.assertResolves("grc-latn", "Ancient Greek (to 1453) (Latin)")

    def test_region_and_extlang_subtags_are_described(self):
        self.assertResolves("nci-mx", "Classical Nahuatl (Mexico)")
        self.assertResolves("zh-yue", "Chinese (Yue Chinese)")

    def test_private_use_subtags_are_labeled_and_kept(self):
        self.assertResolves(
            "zh-latn-pinyin-x-hanyu",
            "Chinese (Latin, Pinyin romanization, private use: hanyu)",
        )

    def test_wholly_private_use_tag_falls_back_to_the_tag_itself(self):
        self.assertResolves("x-local", "x-local (private use)")

    def test_unregistered_primary_subtag_falls_back_to_the_subtag(self):
        # "qqq" is in the private-use range, so it has no registered name, but
        # its region subtag still does.
        self.assertResolves("qqq-002", "qqq (Africa)")

    def test_deprecated_subtag_resolves_to_its_replacement(self):
        self.assertResolves("iw", "Hebrew", Language.RIGHT_TO_LEFT)

    def test_iso_639_2_code_resolves_through_its_two_letter_equivalent(self):
        # "ind" is absent from the IANA registry because "id" is canonical.
        self.assertResolves("ind", "Indonesian")

    def test_direction_comes_from_the_script_a_language_is_written_in(self):
        self.assertResolves("he", "Hebrew", Language.RIGHT_TO_LEFT)

    def test_direction_is_inherited_from_a_macrolanguage(self):
        self.assertResolves("acw", "Hijazi Arabic", Language.RIGHT_TO_LEFT)

    def test_explicit_script_subtag_overrides_the_language_direction(self):
        # Romanized Hebrew reads left to right.
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
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", encoding="utf-8", delete=False
        ) as registry_file:
            registry_file.write(SUBTAG_REGISTRY_FIXTURE)

        added = add_missing_languages(subtag_registry_path=registry_file.name)

        added_by_code = {resolved.code: resolved for resolved in added}
        self.assertEqual(added_by_code["nci"].name, "Classical Nahuatl")
        self.assertEqual(
            added_by_code["zh-latn-wadegile"].name,
            "Chinese (Latin, Wade-Giles romanization)",
        )
        self.assertNotIn("en", added_by_code)

        added_row = Language.objects.get(code="zh-latn-wadegile")
        self.assertEqual(added_row.scope, Language.DATA_SCOPE)
        self.assertFalse(added_row.isdefault)
        self.assertEqual(get_missing_language_codes(), set())

    def test_dry_run_reports_without_writing(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", encoding="utf-8", delete=False
        ) as registry_file:
            registry_file.write(SUBTAG_REGISTRY_FIXTURE)

        added = add_missing_languages(
            subtag_registry_path=registry_file.name, dry_run=True
        )

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
