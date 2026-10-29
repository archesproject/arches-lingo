import { SECONDARY, SUCCESS } from "@/arches_lingo/constants.ts";

import type { useGettext } from "vue3-gettext";
import type {
    MatchLinkImportOutcome,
    MatchLinkImportOutcomeCounts,
    MatchLinkImportOutcomeTotal,
} from "@/arches_lingo/components/generic/MatchLinkImportDialog/types.ts";

type Gettext = ReturnType<typeof useGettext>["$gettext"];

export const MATCH_LINK_IMPORT_POLL_INTERVAL_MS = 2000;
// Consecutive failed status checks before the dialog stops waiting.
export const MATCH_LINK_IMPORT_MAX_FAILED_POLLS = 3;
export const OUTCOME_ADD: MatchLinkImportOutcome = "add";
export const MATCH_LINK_IMPORT_IN_PROGRESS_STATUSES = ["pending", "running"];
export const MATCH_LINK_IMPORT_COMPLETE_STATUS = "complete";

export function describeOutcome(
    outcomeLabels: Record<MatchLinkImportOutcome, string>,
    outcome: MatchLinkImportOutcome,
): string {
    // An outcome added on the server before the client knows it shows as is.
    return outcomeLabels[outcome] ?? outcome;
}

export function outcomeSeverity(outcome: MatchLinkImportOutcome): string {
    return outcome === OUTCOME_ADD ? SUCCESS : SECONDARY;
}

export function summarizeOutcomeCounts(
    $gettext: Gettext,
    outcomeLabels: Record<MatchLinkImportOutcome, string>,
    countsByOutcome: MatchLinkImportOutcomeCounts,
): MatchLinkImportOutcomeTotal[] {
    return (
        Object.entries(countsByOutcome) as [MatchLinkImportOutcome, number][]
    ).map(([outcome, count]) => {
        const label = describeOutcome(outcomeLabels, outcome);
        return {
            outcome,
            count,
            label,
            text: $gettext("%{label}: %{count}", {
                label,
                count: String(count),
            }),
            severity: outcomeSeverity(outcome),
        };
    });
}

export function buildOutcomeLabels(
    $gettext: Gettext,
): Record<MatchLinkImportOutcome, string> {
    return {
        add: $gettext("New link"),
        already_linked: $gettext("Already linked"),
        conflicting_link: $gettext("Already linked with another match type"),
        duplicate_in_file: $gettext("Repeated in this file"),
        unknown_concept: $gettext("Concept not found"),
        outside_scheme: $gettext("Concept is in another scheme"),
        invalid_match_type: $gettext("Unknown match type"),
        invalid_uri: $gettext("Not a web address"),
        self_match: $gettext("The concept's own URI"),
        not_editable: $gettext("Concept cannot be edited in its current state"),
        scheme_locked: $gettext("Scheme is locked"),
    };
}
