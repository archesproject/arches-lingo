import type { ConceptMatchCandidateStatus } from "@/arches_lingo/types.ts";

export const SIGNAL_SHARED_IDENTIFIER = "shared_identifier" as const;
export const SIGNAL_EXACT_LABEL = "exact_label" as const;
export const SIGNAL_TRIGRAM = "trigram" as const;

export const DEFAULT_SIMILARITY_THRESHOLD = 0.7;
export const MIN_SELECTABLE_SIMILARITY = 0.4;
export const MAX_SELECTABLE_SIMILARITY = 0.95;
export const SIMILARITY_STEP = 0.05;

export const RUN_STATUS_PENDING = "pending" as const;
export const RUN_STATUS_RUNNING = "running" as const;
export const RUN_STATUS_COMPLETE = "complete" as const;
export const RUN_STATUS_FAILED = "failed" as const;

export const RUN_POLL_FAILURE_LIMIT = 3;
export const RUN_POLL_INTERVAL_MS = 2000;
export const ELAPSED_CLOCK_TICK_MS = 1000;

export const CANDIDATE_STATUS_PENDING = "pending" as const;
export const CANDIDATE_STATUS_DISMISSED = "dismissed" as const;
export const CANDIDATE_STATUS_LINKED = "linked" as const;
export const CANDIDATE_STATUS_MERGED = "merged" as const;

export const REVIEWABLE_CANDIDATE_STATUSES: readonly ConceptMatchCandidateStatus[] =
    [CANDIDATE_STATUS_PENDING, CANDIDATE_STATUS_DISMISSED];

export const ALL_CANDIDATE_STATUSES: readonly ConceptMatchCandidateStatus[] = [
    CANDIDATE_STATUS_PENDING,
    CANDIDATE_STATUS_DISMISSED,
    CANDIDATE_STATUS_LINKED,
    CANDIDATE_STATUS_MERGED,
];

export const CANNOT_RECEIVE_SCHEME_LOCKED = "scheme_locked" as const;

export const MATCH_TYPE_EXACT = "exactMatch" as const;
export const MATCH_TYPE_CLOSE = "closeMatch" as const;
export const MATCH_TYPE_RELATED = "relatedMatch" as const;

export const CANDIDATES_PER_PAGE = 50;

export const SEARCH_DEBOUNCE_MS = 300;

export const SCHEME_FILTER_MINIMUM_OPTIONS = 8;
