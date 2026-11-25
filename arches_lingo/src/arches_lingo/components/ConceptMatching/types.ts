import type { MatchedConceptSummary } from "@/arches_lingo/types.ts";

export interface CandidateSelectionChange {
    candidateId: number;
    isSelected: boolean;
}

export interface MergeDirection {
    survivor: MatchedConceptSummary;
    absorbed: MatchedConceptSummary;
}
