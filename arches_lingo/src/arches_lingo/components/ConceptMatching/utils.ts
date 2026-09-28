import {
    ALL_CANDIDATE_STATUSES,
    BRIEF_RUN_SECONDS,
    CANDIDATE_STATUS_PENDING,
    DURATION_SPAN_HIGH_FACTOR,
    DURATION_SPAN_LOW_FACTOR,
    FUZZY_RUN_FIXED_SECONDS,
    FUZZY_RUN_SECONDS_PER_LABEL,
    LONG_RUN_MINUTES,
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
    MatchedConceptSummary,
    SearchResultItem,
} from "@/arches_lingo/types.ts";
import type { ExpectedDuration } from "@/arches_lingo/components/ConceptMatching/types.ts";

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

/**
 * A candidate stores its concepts lowest id first rather than in any meaningful
 * order, so neither side can be assumed to be the survivor.
 */
export function resolveMergeSides(
    conceptA: MatchedConceptSummary,
    conceptB: MatchedConceptSummary,
    absorbedConceptId: string,
): { survivor: MatchedConceptSummary; absorbed: MatchedConceptSummary } {
    const absorbedIsFirst = conceptA.id === absorbedConceptId;
    return {
        survivor: absorbedIsFirst ? conceptB : conceptA,
        absorbed: absorbedIsFirst ? conceptA : conceptB,
    };
}

/**
 * The absorbed concept in the shape the merge dialog's picker emits. Only the
 * id and labels are read from it, so the rest only satisfies the type.
 */
export function buildPreselectedConcept(
    concept: MatchedConceptSummary,
): SearchResultItem {
    return {
        id: concept.id,
        labels: concept.labels,
        parents: [],
        polyhierarchical: false,
    };
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
 * No schemes means every label, including those belonging to no scheme, which
 * is what an unscoped run compares.
 */
export function labelsInScope(
    selectedSchemeIds: string[],
    totalLabels: number,
    labelsByScheme: Record<string, number>,
): number {
    if (!selectedSchemeIds.length) {
        return totalLabels;
    }
    return selectedSchemeIds.reduce(
        (runningTotal, schemeId) =>
            runningTotal + (labelsByScheme[schemeId] ?? 0),
        0,
    );
}

export function estimateFuzzyRunSeconds(labelCount: number): number {
    return FUZZY_RUN_FIXED_SECONDS + labelCount * FUZZY_RUN_SECONDS_PER_LABEL;
}

export function estimateDurationSpan(labelCount: number): ExpectedDuration {
    const seconds = estimateFuzzyRunSeconds(labelCount);
    if (seconds < BRIEF_RUN_SECONDS) {
        return { kind: "brief" };
    }

    const lowMinutes = Math.max(
        1,
        Math.floor((seconds * DURATION_SPAN_LOW_FACTOR) / 60),
    );
    const highMinutes = Math.ceil((seconds * DURATION_SPAN_HIGH_FACTOR) / 60);
    if (highMinutes >= LONG_RUN_MINUTES) {
        return { kind: "overAnHour" };
    }
    return { kind: "minutes", lowMinutes, highMinutes };
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
