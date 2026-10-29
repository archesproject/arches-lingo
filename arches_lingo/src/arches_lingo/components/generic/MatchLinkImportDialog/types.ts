export type MatchLinkImportOutcome =
    | "add"
    | "already_linked"
    | "conflicting_link"
    | "duplicate_in_file"
    | "unknown_concept"
    | "outside_scheme"
    | "invalid_match_type"
    | "invalid_uri"
    | "self_match"
    | "not_editable"
    | "scheme_locked";

export type MatchLinkImportOutcomeCounts = Partial<
    Record<MatchLinkImportOutcome, number>
>;

export interface MatchLinkImportLink {
    row_number: number;
    concept_id: string;
    concept_label: string | null;
    match_uri: string;
    match_type: string;
    outcome: MatchLinkImportOutcome;
    is_internal_concept: boolean;
}

export interface MatchLinkImportPreview {
    total_links: number;
    counts_by_outcome: MatchLinkImportOutcomeCounts;
    links: MatchLinkImportLink[];
}

export interface MatchLinkImportRecord {
    id: number;
    filename: string;
    status: "pending" | "running" | "complete" | "failed";
    scheme_id: string | null;
    created: string;
    finished: string | null;
    total_links: number;
    outcome_counts: MatchLinkImportOutcomeCounts;
    error_message: string;
}

export interface MatchLinkImportOutcomeTotal {
    outcome: MatchLinkImportOutcome;
    count: number;
    label: string;
    text: string;
    severity: string;
}
