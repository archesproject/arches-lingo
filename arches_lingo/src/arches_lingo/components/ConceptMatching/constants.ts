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

// Linked and merged are records of work done to the concepts themselves, so
// they are shown but not decided again from the queue.
export const REVIEWABLE_CANDIDATE_STATUSES: readonly ConceptMatchCandidateStatus[] =
    [CANDIDATE_STATUS_PENDING, CANDIDATE_STATUS_DISMISSED];

export const ALL_CANDIDATE_STATUSES: readonly ConceptMatchCandidateStatus[] = [
    CANDIDATE_STATUS_PENDING,
    CANDIDATE_STATUS_DISMISSED,
    CANDIDATE_STATUS_LINKED,
    CANDIDATE_STATUS_MERGED,
];

export const CANDIDATES_PER_PAGE = 50;

export const SCHEME_FILTER_MINIMUM_OPTIONS = 8;

// A fixed cost plus a cost per label, fitted to runs measured on a
// 740,559-label corpus. The fit is loose, so it is only ever shown as a span
// (widened upwards) rather than a single figure, and it depends on the
// server's hardware rather than on the data.
export const FUZZY_RUN_FIXED_SECONDS = 17;
export const FUZZY_RUN_SECONDS_PER_LABEL = 0.0018;
export const DURATION_SPAN_LOW_FACTOR = 0.7;
export const DURATION_SPAN_HIGH_FACTOR = 1.4;
export const BRIEF_RUN_SECONDS = 90;
export const LONG_RUN_MINUTES = 60;
