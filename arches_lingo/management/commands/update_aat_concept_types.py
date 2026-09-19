"""
Management command: update_aat_concept_types
=============================================

Reads the AAT SKOS XML produced by ``utils.aat.skos_conversion`` and updates the
concept type tiles for resources already loaded into arches-lingo to reflect the
correct AAT concept type: "concept", "guide term", "hierarchy name", or "facet".

Run by ``load_aat`` after the import. See ``utils.aat.concept_types`` for how
each type is recognised and what reference data it needs.
"""

from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError

from arches_lingo.utils.aat.concept_types import (
    MissingConceptTypeItemsError,
    load_non_concept_type_items,
    parse_aat_concept_types,
    update_concept_type_tiles,
)


class Command(BaseCommand):
    help = (
        "Updates concept type tiles for AAT concepts already loaded into "
        "arches-lingo, assigning the correct type (guide term, hierarchy name, "
        "or facet) based on patterns in the AAT SKOS export file."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            "-s",
            required=True,
            help="Path to the AAT SKOS XML file (e.g. getty_aat_skos.xml).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help=("Print what would be updated without making any database changes."),
        )

    def handle(self, *args, **options):
        skos_path = options["source"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry-run mode: no changes will be saved.")
            )

        self.stdout.write("Loading concept type list items from database ...")
        try:
            type_items_by_label = load_non_concept_type_items()
        except MissingConceptTypeItemsError as missing_items_error:
            raise CommandError(str(missing_items_error)) from missing_items_error
        self.stdout.write(f"  Found list items for: {sorted(type_items_by_label)}")

        self.stdout.write(f"Parsing AAT SKOS file: {skos_path} ...")
        non_concept_type_map = parse_aat_concept_types(skos_path)

        uris_by_type = defaultdict(list)
        for aat_uri, type_label in non_concept_type_map.items():
            uris_by_type[type_label].append(aat_uri)

        for type_label in sorted(uris_by_type):
            self.stdout.write(
                f"  {len(uris_by_type[type_label]):>5} {type_label!r} concepts identified"
            )

        self.stdout.write("Updating concept type tiles ...")
        updated_counts = update_concept_type_tiles(
            uris_by_type, type_items_by_label, dry_run=dry_run
        )

        total = sum(updated_counts.values())
        for type_label, count in sorted(updated_counts.items()):
            verb = "would update" if dry_run else "updated"
            self.stdout.write(f"  {count:>5} tiles {verb} → {type_label!r}")

        verb = "would be updated" if dry_run else "updated"
        self.stdout.write(
            self.style.SUCCESS(f"Done. {total} concept type tiles {verb}.")
        )
