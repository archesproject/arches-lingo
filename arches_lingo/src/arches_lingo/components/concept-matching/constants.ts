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

// What a fuzzy run costs, as a fixed cost per slice plus a cost per label it
// has to compare. Measured on a 740,559-label corpus:
//
//     8,167 labels ->   32s      201,112 ->  272s
//   530,778        -> 1080s      740,559 -> 1357s
//
// The relationship is not really a straight line -- it runs below one at the
// small end and above it at the large -- so these two terms are within a few
// per cent at both ends and overestimate the middle by about a third. That is
// why the figure is never shown on its own: the span it is shown as brackets
// all four, and erring long is the kinder direction for a warning.
//
// These are properties of the server rather than of the data, so an
// installation on very different hardware would want different numbers.
export const FUZZY_RUN_FIXED_SECONDS = 17;
export const FUZZY_RUN_SECONDS_PER_LABEL = 0.0018;
