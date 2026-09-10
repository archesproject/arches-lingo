"""Load the Getty Art & Architecture Thesaurus from the Getty bulk export."""

import os
import tempfile

from django.core.management.base import BaseCommand, CommandError

from arches_lingo import const
from arches_lingo.utils.aat.pipeline import load_aat
from arches_lingo.utils.aat.skos_conversion import (
    DEFAULT_SCHEME_IDENTIFIER_URI,
    DEFAULT_SCHEME_PREF_LABEL,
    GETTY_AAT_EXPLICIT_ZIP_URL,
    AATConversionError,
)


class Command(BaseCommand):
    help = (
        "Download the Getty AAT bulk export and load it as Lingo concepts, "
        "including labels, scope notes, hierarchy, typed relations, identifiers "
        "and source/contributor attribution. Re-running replaces the previously "
        "loaded AAT data while leaving other schemes untouched."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--archive",
            default="",
            help=(
                "Path to an already-downloaded Getty archive. Omit to download "
                f"from {GETTY_AAT_EXPLICIT_ZIP_URL}."
            ),
        )
        parser.add_argument(
            "--url",
            default=GETTY_AAT_EXPLICIT_ZIP_URL,
            help=(
                "Archive URL to download. Defaults to the explicit export, which "
                "Getty still updates; their full export has been frozen since "
                "January 2025."
            ),
        )
        parser.add_argument(
            "--working-directory",
            default="",
            help=(
                "Directory for the intermediate SKOS and attribution files. "
                "Defaults to a temporary directory that is left in place so a "
                "failed run can be resumed."
            ),
        )
        parser.add_argument(
            "--scheme-pref-label",
            default=DEFAULT_SCHEME_PREF_LABEL,
            help=f"English label for the scheme (default: {DEFAULT_SCHEME_PREF_LABEL!r}).",
        )
        parser.add_argument(
            "--scheme-identifier",
            default=DEFAULT_SCHEME_IDENTIFIER_URI,
            help=f"URL-valued identifier for the scheme (default: {DEFAULT_SCHEME_IDENTIFIER_URI}).",
        )
        parser.add_argument(
            "--lifecycle-state",
            choices=sorted(const.LIFECYCLE_STATE_IDS_BY_NAME),
            default="locked",
            help=(
                "Lifecycle state for the loaded scheme and its concepts. "
                "Defaults to locked, which prevents editing a vocabulary that "
                "mirrors an external authority."
            ),
        )
        parser.add_argument(
            "--index",
            action="store_true",
            help=(
                "Write the loaded resources to Elasticsearch. Off by default: "
                "indexing is the slowest part of the load and many Lingo "
                "deployments do not query the index. Descriptors are always "
                "recalculated, so names display correctly either way."
            ),
        )
        parser.add_argument(
            "--no-progress",
            action="store_true",
            help=(
                "Suppress the progress bars shown while reading the export. "
                "They are suppressed automatically when output is redirected."
            ),
        )
        parser.add_argument(
            "--keep-existing",
            action="store_true",
            help=(
                "Import alongside the currently loaded AAT data instead of "
                "replacing it. Leaves concepts Getty has retired in place."
            ),
        )
        parser.add_argument(
            "--new-resource-ids",
            action="store_true",
            help=(
                "Assign fresh resource ids to every concept instead of reusing "
                "the ids a previous load gave them. Breaks references held "
                "elsewhere to AAT concepts."
            ),
        )

    def handle(self, *args, **options):
        working_directory = options["working_directory"] or os.path.join(
            tempfile.gettempdir(), "arches_lingo_aat"
        )
        try:
            result = load_aat(
                working_directory,
                archive_path=options["archive"] or None,
                archive_url=options["url"],
                scheme_identifier_uri=options["scheme_identifier"],
                scheme_pref_label=options["scheme_pref_label"],
                replace_existing=not options["keep_existing"],
                preserve_resource_ids=not options["new_resource_ids"],
                lifecycle_state_id=const.LIFECYCLE_STATE_IDS_BY_NAME[
                    options["lifecycle_state"]
                ],
                skip_indexing=not options["index"],
                show_progress=False if options["no_progress"] else None,
                log=lambda message: self.stdout.write(str(message)),
            )
        except AATConversionError as conversion_error:
            raise CommandError(str(conversion_error)) from conversion_error

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {result['concepts']:,} AAT concepts "
                f"into scheme {result['scheme_id']}"
            )
        )
        if result["extraction_date"]:
            self.stdout.write(
                f"Getty export extracted on {result['extraction_date'].isoformat()}; "
                "the attribution statement recorded on the scheme names that date."
            )
