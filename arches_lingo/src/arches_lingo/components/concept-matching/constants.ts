// Mirrors the server's signal names; see utils/concept_matching.py.
export const SIGNAL_SHARED_IDENTIFIER = "shared_identifier";
export const SIGNAL_EXACT_LABEL = "exact_label";
export const SIGNAL_TRIGRAM = "trigram";

// Postgres defaults trigram similarity to 0.3, which on a vocabulary the size
// of the AAT returns around 87 candidates per label. See the server's
// DEFAULT_SIMILARITY_THRESHOLD.
export const DEFAULT_SIMILARITY_THRESHOLD = 0.7;

export const RUN_STATUS_PENDING = "pending";
export const RUN_STATUS_RUNNING = "running";
export const RUN_STATUS_FAILED = "failed";

// A fuzzy run is handed to a worker, so its progress is polled.
export const RUN_POLL_INTERVAL_MS = 2000;

export const CANDIDATE_STATUS_PENDING = "pending";
export const CANDIDATE_STATUS_DISMISSED = "dismissed";

export const CANDIDATES_PER_PAGE = 50;
