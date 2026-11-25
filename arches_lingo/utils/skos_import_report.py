from collections import Counter
from dataclasses import asdict, dataclass, field

from django.utils.translation import gettext as _, ngettext

PREDICATES_NAMED_IN_SUMMARY = 5


@dataclass
class SkosImportReport:
    """What a SKOS import read but could not turn into Lingo data.

    Someone importing through the user interface cannot see the server log, so
    this is how they learn that part of their file was left out.
    """

    collection_count: int = 0
    collection_member_count: int = 0
    concepts_outside_schemes_count: int = 0
    unresolved_match_count: int = 0
    skipped_predicate_counts: Counter = field(default_factory=Counter)

    def is_empty(self):
        return not any(
            (
                self.collection_count,
                self.collection_member_count,
                self.concepts_outside_schemes_count,
                self.unresolved_match_count,
                self.skipped_predicate_counts,
            )
        )

    def as_dict(self):
        report = asdict(self)
        report["skipped_predicate_counts"] = dict(self.skipped_predicate_counts)
        return report

    def summary(self):
        """Return one sentence naming what was not imported, or None."""
        if self.is_empty():
            return None
        return _("Not imported: {items}.").format(
            items="; ".join(self._summary_items())
        )

    def _summary_items(self):
        items = []
        if self.collection_count:
            items.append(
                ngettext(
                    "{count} skos:Collection",
                    "{count} skos:Collection resources",
                    self.collection_count,
                ).format(count=self.collection_count)
            )
        if self.collection_member_count:
            items.append(
                ngettext(
                    "{count} skos:member statement",
                    "{count} skos:member statements",
                    self.collection_member_count,
                ).format(count=self.collection_member_count)
            )
        if self.concepts_outside_schemes_count:
            items.append(
                ngettext(
                    "{count} concept that is not in any scheme in the file",
                    "{count} concepts that are not in any scheme in the file",
                    self.concepts_outside_schemes_count,
                ).format(count=self.concepts_outside_schemes_count)
            )
        if self.unresolved_match_count:
            items.append(
                ngettext(
                    "{count} match with no target URI",
                    "{count} matches with no target URI",
                    self.unresolved_match_count,
                ).format(count=self.unresolved_match_count)
            )

        most_common = self.skipped_predicate_counts.most_common()
        for predicate, count in most_common[:PREDICATES_NAMED_IN_SUMMARY]:
            items.append(
                ngettext(
                    "{count} {predicate} statement",
                    "{count} {predicate} statements",
                    count,
                ).format(count=count, predicate=predicate)
            )
        remaining_count = sum(
            count for _predicate, count in most_common[PREDICATES_NAMED_IN_SUMMARY:]
        )
        if remaining_count:
            items.append(
                ngettext(
                    "{count} statement with another unsupported property",
                    "{count} statements with other unsupported properties",
                    remaining_count,
                ).format(count=remaining_count)
            )
        return items
