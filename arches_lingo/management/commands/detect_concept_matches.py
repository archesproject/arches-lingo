"""Management command: detect_concept_matches

Run match detection over a scope and store the result as a reviewable run.

Matching a whole vocabulary is slow enough that it is worth starting from the
command line rather than a request, and this is also the escape hatch when no
celery worker is available. The run it writes is the same one the interface
reads, so any editor can review it in the browser; without --user it has no
creator, and only a Lingo admin can delete it.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from arches_lingo.models import ConceptMatchCandidate
from arches_lingo.utils.concept_matching import (
    ALL_SIGNALS,
    DEFAULT_SIMILARITY_THRESHOLD,
    EXACT_SIGNALS,
    MAX_SIMILARITY_THRESHOLD,
    MIN_SIMILARITY_THRESHOLD,
    ConceptMatchError,
    MatchScope,
    run_detection,
)


class Command(BaseCommand):
    help = (
        "Find concepts that probably mean the same thing and store them as a "
        "reviewable match run. Compares URIs and labels, exactly or by "
        "similarity; scope the run with --scheme, --concept-set or --concept."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--scheme",
            action="append",
            default=[],
            dest="schemes",
            help=(
                "Confine the run to this scheme (resource id). Repeatable; "
                "both concepts of a pair must be in one of the schemes given, "
                "so the run never reaches outside them."
            ),
        )
        parser.add_argument(
            "--concept-set",
            type=int,
            default=None,
            help="Only keep pairs involving a member of this concept set.",
        )
        parser.add_argument(
            "--concept",
            action="append",
            default=[],
            dest="concepts",
            help=(
                "Only keep pairs involving this concept. Repeatable, and "
                "combines with the other scoping options."
            ),
        )
        parser.add_argument(
            "--cross-scheme-only",
            action="store_true",
            help="Discard pairs whose concepts are in the same scheme.",
        )
        parser.add_argument(
            "--signal",
            action="append",
            choices=sorted(ALL_SIGNALS),
            default=[],
            dest="signals",
            help=(
                "Signal to run. Repeatable; defaults to the exact signals. "
                "shared_identifier compares URIs, exact_label compares labels, "
                "trigram finds similar labels."
            ),
        )
        parser.add_argument(
            "--similarity-threshold",
            type=float,
            default=DEFAULT_SIMILARITY_THRESHOLD,
            help=(
                "How similar two labels must be for the trigram signal, from "
                f"{MIN_SIMILARITY_THRESHOLD} to {MAX_SIMILARITY_THRESHOLD}. "
                f"Defaults to {DEFAULT_SIMILARITY_THRESHOLD}."
            ),
        )
        parser.add_argument(
            "--any-language",
            action="store_true",
            help=(
                "Treat labels in different languages as a match. Off by "
                "default, since the same spelling in two languages is often a "
                "coincidence rather than a duplicate."
            ),
        )
        parser.add_argument(
            "--user",
            default="",
            help="Username to record as the run's owner.",
        )

    def handle(self, *args, **options):
        run_owner = None
        if options["user"]:
            try:
                run_owner = User.objects.get(username=options["user"])
            except User.DoesNotExist:
                raise CommandError(f"No such user: {options['user']}")

        scope = MatchScope(
            scheme_ids=options["schemes"],
            source_concept_set_id=options["concept_set"],
            source_concept_ids=options["concepts"],
            cross_scheme_only=options["cross_scheme_only"],
        )

        self.stdout.write("Detecting concept matches ...")
        try:
            run = run_detection(
                scope,
                signals=tuple(options["signals"]) or EXACT_SIGNALS,
                same_language_only=not options["any_language"],
                similarity_threshold=options["similarity_threshold"],
                user=run_owner,
                log=lambda message: self.stdout.write(str(message)),
            )
        except ConceptMatchError as detection_error:
            raise CommandError(str(detection_error)) from detection_error

        # Deleting a run from the interface is how it is cancelled.
        if run is None:
            self.stdout.write(self.style.WARNING("The run was cancelled."))
            return

        counts_by_signal = {}
        for signal, _label in ConceptMatchCandidate.SIGNAL_CHOICES:
            signal_count = run.candidates.filter(signal=signal).count()
            if signal_count:
                counts_by_signal[signal] = signal_count

        for signal, signal_count in sorted(counts_by_signal.items()):
            self.stdout.write(f"  {signal_count:>7,} from {signal}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Run {run.pk} complete: {run.candidate_count:,} candidate pair(s)."
            )
        )
