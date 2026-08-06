"""Dump a portable, compressed snapshot of all arches-lingo concept/scheme
resource data (and everything it references) to a single tar.gz archive,
saved through Django's default file storage.

Example:
    python manage.py dump_lingo_fixtures --key lingo_fixtures/lingo_concept_scheme_fixture.tar.gz
"""

from django.core.management.base import BaseCommand

from arches_lingo.utils.lingo_fixtures import (
    DEFAULT_FIXTURE_STORAGE_KEY,
    dump_lingo_fixtures,
)


class Command(BaseCommand):
    help = (
        "Dump all arches-lingo concept/scheme resource data (resources, tiles, "
        "files, resource-to-resource relations, resource identifiers, "
        "per-scheme identifier/URI/attribution records, and the language "
        "records the data's language codes need) plus the associated uploaded "
        "files to a single compressed archive in the default file storage."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--key",
            default=DEFAULT_FIXTURE_STORAGE_KEY,
            help=(
                "Default file storage key/path for the compressed archive "
                f"(default: {DEFAULT_FIXTURE_STORAGE_KEY})."
            ),
        )

    def handle(self, *args, **options):
        row_counts = dump_lingo_fixtures(options["key"])

        self.stdout.write(
            self.style.SUCCESS(f"Wrote fixture archive to storage key {options['key']}")
        )
        for table_name, row_count in row_counts.items():
            self.stdout.write(f"  {table_name}: {row_count}")
