import {
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
 * Why a pair was suggested, in words.
 *
 * `translate` is the caller's $gettext, so the wording stays translatable while
 * the branching stays testable.
 */
export function describeMatchReason(
    candidate: ConceptMatchCandidate,
    translate: (message: string, options: Record<string, string>) => string,
): string {
    if (candidate.signal === SIGNAL_SHARED_IDENTIFIER) {
        return translate("Same URI: %{evidence}", {
            evidence: candidate.evidence,
        });
    }
    if (candidate.signal === SIGNAL_TRIGRAM) {
        return translate("Similar labels (%{score}): %{evidence}", {
            score: candidate.score.toFixed(2),
            evidence: candidate.evidence,
        });
    }
    return translate("Same label: %{evidence}", {
        evidence: candidate.evidence,
    });
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
