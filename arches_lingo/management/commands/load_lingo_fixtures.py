"""Restore a snapshot previously written by `dump_lingo_fixtures`: loads the
database tables with PostgreSQL COPY inside a single deferred-constraint
transaction, restores the accompanying uploaded files into the configured
file storage, and reindexes the affected resources in Elasticsearch.

Example:
    python manage.py load_lingo_fixtures --key lingo_fixtures/lingo_concept_scheme_fixture.tar.gz
"""

from django.core.management.base import BaseCommand, CommandError

from arches_lingo.utils.lingo_fixtures import (
    DEFAULT_FIXTURE_STORAGE_KEY,
    get_lingo_fixture_graph_ids,
    load_lingo_fixtures,
)


class Command(BaseCommand):
    help = (
        "Restore a fixture archive previously written by dump_lingo_fixtures "
        "from the default file storage."
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
        parser.add_argument(
            "--no-index",
            action="store_true",
            help="Skip reindexing the restored resources in Elasticsearch.",
        )

    def handle(self, *args, **options):
        try:
            row_counts = load_lingo_fixtures(
                options["key"], index=not options["no_index"]
            )
        except LookupError as lookup_error:
            raise CommandError(str(lookup_error)) from lookup_error

        self.stdout.write(self.style.SUCCESS("Restored fixture archive."))
        for table_name, row_count in row_counts.items():
            if row_count is None:
                self.stdout.write(f"  {table_name}: not present in this archive")
            else:
                self.stdout.write(f"  {table_name}: {row_count}")

        if options["no_index"]:
            graph_ids = get_lingo_fixture_graph_ids()
            self.stdout.write(
                self.style.WARNING(
                    "Skipped reindexing. Run 'python manage.py es index_resources_by_type "
                    f"-rt {','.join(str(graph_id) for graph_id in graph_ids)}' "
                    "before relying on search/UI results."
                )
            )
