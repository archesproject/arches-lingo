import {
    ALL_CANDIDATE_STATUSES,
    CANDIDATE_STATUS_PENDING,
    RUN_STATUS_PENDING,
    RUN_STATUS_RUNNING,
    SIGNAL_EXACT_LABEL,
    SIGNAL_SHARED_IDENTIFIER,
    SIGNAL_TRIGRAM,
} from "@/arches_lingo/components/ConceptMatching/constants.ts";

import type {
    ConceptMatchCandidateStatus,
    ConceptMatchRun,
    ConceptMatchSignal,
} from "@/arches_lingo/types.ts";

/**
 * Ordered strongest first to match the server, which keeps the best reason when
 * more than one signal suggests the same pair.
 */
export function buildSignalList(options: {
    compareUris: boolean;
    compareLabels: boolean;
    compareSimilarLabels: boolean;
}): ConceptMatchSignal[] {
    const signals: ConceptMatchSignal[] = [];
    if (options.compareUris) signals.push(SIGNAL_SHARED_IDENTIFIER);
    if (options.compareLabels) signals.push(SIGNAL_EXACT_LABEL);
    if (options.compareSimilarLabels) signals.push(SIGNAL_TRIGRAM);
    return signals;
}

export function isRunUnfinished(run: ConceptMatchRun): boolean {
    return (
        run.status === RUN_STATUS_PENDING || run.status === RUN_STATUS_RUNNING
    );
}

export function describeSkippedReasons(
    skipped: Record<string, number>,
    describeReason: (reason: string, count: number) => string,
    languageCode: string,
): string {
    return new Intl.ListFormat(languageCode, { type: "conjunction" }).format(
        Object.entries(skipped).map(([reason, count]) =>
            describeReason(reason, count),
        ),
    );
}

export function splitElapsedSeconds(totalSeconds: number): {
    minutes: number;
    seconds: number;
} {
    const wholeSeconds = Math.max(0, Math.floor(totalSeconds));
    return {
        minutes: Math.floor(wholeSeconds / 60),
        seconds: wholeSeconds % 60,
    };
}

/**
 * Anything the interface does not offer falls back to the outstanding pairs,
 * so a hand-edited or outdated link still lands somewhere sensible.
 */
export function candidateStatusFromRoute(
    rawStatus: unknown,
): ConceptMatchCandidateStatus {
    return (
        ALL_CANDIDATE_STATUSES.find(
            (candidateStatus) => candidateStatus === rawStatus,
        ) ?? CANDIDATE_STATUS_PENDING
    );
}
