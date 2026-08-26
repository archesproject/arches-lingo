import csv
import io
import tarfile

from django.db import connection
from django.test import TestCase

from arches.app.models.models import Language

from arches_lingo.utils.lingo_fixtures import FIXTURE_TABLES, _copy_table_from_tar

# these tests can be run from the command line via
# python manage.py test tests.test_lingo_fixtures --settings="tests.test_settings"


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
