import type { MatchLinkImportOutcome } from "@/arches_lingo/types.ts";

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

export function buildOutcomeLabels(
    $gettext: (text: string) => string,
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
