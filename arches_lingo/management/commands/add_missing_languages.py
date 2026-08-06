"""Add a `languages` row for every language code that appears in resource data
but has no row yet, so the Language widget can resolve a name for it.

Example:
    python manage.py add_missing_languages --dry-run
    python manage.py add_missing_languages
"""

from django.core.management.base import BaseCommand

from arches.app.models.models import Language

from arches_lingo.utils.data_languages import add_missing_languages


class Command(BaseCommand):
    help = (
        "Detect the language codes used by resource data that have no row in the "
        "languages table, and add one for each with the best available name and "
        "text direction derived from Django's language list and the IANA Language "
        "Subtag Registry."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be added without writing anything.",
        )
        parser.add_argument(
            "--scope",
            default=Language.DATA_SCOPE,
            choices=[Language.DATA_SCOPE, Language.SYSTEM_SCOPE],
            help=(
                "Scope for the added rows (default: "
                f"{Language.DATA_SCOPE}, for languages the data is recorded in "
                "rather than languages the interface is translated into)."
            ),
        )
        parser.add_argument(
            "--subtag-registry",
            help=(
                "Path to a local copy of the IANA Language Subtag Registry. "
                "Downloaded from iana.org when not given."
            ),
        )

    def handle(self, *args, **options):
        resolved_languages = add_missing_languages(
            subtag_registry_path=options["subtag_registry"],
            scope=options["scope"],
            dry_run=options["dry_run"],
        )

        if not resolved_languages:
            self.stdout.write(
                self.style.SUCCESS(
                    "Every language code used by resource data already has a row."
                )
            )
            return

        for resolved in resolved_languages:
            self.stdout.write(
                f"  {resolved.code}: {resolved.name} ({resolved.default_direction})"
            )

        summary = f"{len(resolved_languages)} language(s)"
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"Dry run: {summary} would be added."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Added {summary}."))
