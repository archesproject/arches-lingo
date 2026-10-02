export type ExpectedDuration =
    | { kind: "brief" }
    | { kind: "overAnHour" }
    | { kind: "minutes"; lowMinutes: number; highMinutes: number };

export interface CandidateSelectionChange {
    candidateId: number;
    isSelected: boolean;
}

export interface MergeDirection {
    survivorId: string;
    absorbedId: string;
}
