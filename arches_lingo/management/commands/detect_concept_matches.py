"""Management command: detect_concept_matches

Run match detection over a scope and store the result as a reviewable run.

Matching a whole vocabulary is slow enough that it is worth starting from the
command line rather than a request, and this is also the escape hatch when no
celery worker is available. The run it writes is the same one the interface
reads, so a run started here can be reviewed in the browser.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from arches_lingo.models import ConceptMatchCandidate
from arches_lingo.utils.concept_matching import (
    EXACT_SIGNALS,
    ConceptMatchError,
    MatchScope,
    run_detection,
)


class Command(BaseCommand):
    help = (
        "Find concepts that probably mean the same thing and store them as a "
        "reviewable match run. Compares labels and URIs; scope the run with "
        "--source-scheme, --target-scheme or --concept-set."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-scheme",
            default="",
            help="Only keep pairs with a concept in this scheme (resource id).",
        )
        parser.add_argument(
            "--target-scheme",
            default="",
            help="Only keep pairs with a concept in this scheme (resource id).",
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
            choices=sorted(EXACT_SIGNALS),
            default=[],
            dest="signals",
            help=(
                "Signal to run. Repeatable; defaults to every signal. "
                "shared_identifier compares URIs, exact_label compares labels."
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
            source_scheme_id=options["source_scheme"] or None,
            target_scheme_id=options["target_scheme"] or None,
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
                user=run_owner,
                log=lambda message: self.stdout.write(str(message)),
            )
        except ConceptMatchError as detection_error:
            raise CommandError(str(detection_error)) from detection_error

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
