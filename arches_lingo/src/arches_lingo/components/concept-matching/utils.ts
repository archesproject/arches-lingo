import {
    ALL_CANDIDATE_STATUSES,
    CANDIDATE_STATUS_PENDING,
    FUZZY_RUN_FIXED_SECONDS,
    FUZZY_RUN_SECONDS_PER_LABEL,
    RUN_STATUS_PENDING,
    RUN_STATUS_RUNNING,
    SIGNAL_EXACT_LABEL,
    SIGNAL_SHARED_IDENTIFIER,
    SIGNAL_TRIGRAM,
} from "@/arches_lingo/components/concept-matching/constants.ts";

import type {
    ConceptMatchCandidate,
    ConceptMatchRun,
    MatchedConceptSummary,
    SearchResultItem,
} from "@/arches_lingo/types.ts";

/**
 * Which signals to ask for, from what the reviewer ticked.
 *
 * Ordered strongest first to match the server, which keeps the best reason when
 * more than one signal suggests the same pair.
 */
export function buildSignalList(options: {
    compareUris: boolean;
    compareLabels: boolean;
    compareSimilarLabels: boolean;
}): string[] {
    const signals: string[] = [];
    if (options.compareUris) signals.push(SIGNAL_SHARED_IDENTIFIER);
    if (options.compareLabels) signals.push(SIGNAL_EXACT_LABEL);
    if (options.compareSimilarLabels) signals.push(SIGNAL_TRIGRAM);
    return signals;
}

/**
 * Whether a run still has work to do.
 *
 * A fuzzy run is handed to a worker and comes back before it has found
 * anything, so "no candidates yet" is not the same as "no candidates".
 */
export function isRunUnfinished(run: ConceptMatchRun): boolean {
    return (
        run.status === RUN_STATUS_PENDING || run.status === RUN_STATUS_RUNNING
    );
}

/**
 * The two sides of a pair, once the reviewer has chosen which one survives.
 *
 * A candidate stores its concepts lowest id first rather than in any meaningful
 * order, so neither side can be assumed to be the survivor.
 */
export function resolveMergeSides(
    candidate: ConceptMatchCandidate,
    absorbedConceptId: string,
): { survivor: MatchedConceptSummary; absorbed: MatchedConceptSummary } {
    const absorbedIsFirst = candidate.concept_a.id === absorbedConceptId;
    return {
        survivor: absorbedIsFirst ? candidate.concept_b : candidate.concept_a,
        absorbed: absorbedIsFirst ? candidate.concept_a : candidate.concept_b,
    };
}

/**
 * The absorbed concept in the shape the merge dialog's picker emits.
 *
 * Only the id and labels are read from it -- the id to fetch the resource, the
 * labels to name it -- so the rest is filled in to satisfy the type.
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

/**
 * The pairs a link request could not act on, named so the reviewer can tell
 * whether it is worth doing anything about.
 */
export function describeSkippedReasons(
    skipped: Record<string, number>,
    reasonLabels: Record<string, string>,
): string {
    return Object.entries(skipped)
        .map(
            ([reason, count]) => `${count} (${reasonLabels[reason] ?? reason})`,
        )
        .join(", ");
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
 * How many labels a run over these schemes would have to compare.
 *
 * No schemes means every label, including those belonging to no scheme, which
 * is what an unscoped run actually compares.
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

/**
 * The estimate as a span rather than a single figure.
 *
 * It is built from a straight line fitted to a handful of measurements, so a
 * single number would claim a precision it does not have. The span is widened
 * upwards because a run taking longer than promised is the unpleasant surprise,
 * and one finishing early is not.
 */
export type ExpectedDuration =
    | { kind: "brief" }
    | { kind: "overAnHour" }
    | { kind: "minutes"; lowMinutes: number; highMinutes: number };

export function estimateDurationSpan(labelCount: number): ExpectedDuration {
    const seconds = estimateFuzzyRunSeconds(labelCount);
    if (seconds < 90) {
        return { kind: "brief" };
    }

    const lowMinutes = Math.max(1, Math.floor((seconds * 0.7) / 60));
    const highMinutes = Math.ceil((seconds * 1.4) / 60);
    if (highMinutes >= 60) {
        return { kind: "overAnHour" };
    }
    return { kind: "minutes", lowMinutes, highMinutes };
}

/**
 * Which queue a `status` in the address refers to.
 *
 * Anything the interface does not offer falls back to the outstanding pairs,
 * so a hand-edited or outdated link lands somewhere sensible rather than on an
 * empty list explained by nothing.
 */
export function candidateStatusFromRoute(rawStatus: unknown): string {
    const status = String(rawStatus ?? "");
    return ALL_CANDIDATE_STATUSES.includes(status)
        ? status
        : CANDIDATE_STATUS_PENDING;
}
