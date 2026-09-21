import type { AliasedNodeData } from "@/arches_vue_components/types.ts";
import type { MergeRetirementStrategy } from "@/arches_lingo/types.ts";

export interface MergeTile {
    tileid?: string;
    aliased_data: Record<string, AliasedNodeData | undefined>;
}

export interface MergeSection {
    nodegroupAlias: string;
    cardinality: "1" | "n";
    displayNodeAliases: string[];
    identityNodeAliases: string[] | null;
    // Display nodes holding references to other concepts. Their names come from
    // getItemLabel against fetched labels, not from the tile's display_value,
    // which is the resource descriptor rather than a language-aware label.
    conceptReferenceNodeAliases?: string[];
    // Holds a reference that only means anything inside one scheme, so it is
    // never brought across from a concept in another. Mirrors the server's
    // SCHEME_SCOPED_NODEGROUP_ALIASES.
    schemeScoped?: boolean;
}

export interface MergeTileOption {
    tile: MergeTile;
    identityKey: string | null;
    alreadyOnSurvivor: boolean;
    isSelected: boolean;
}

export interface SectionComparison {
    section: MergeSection;
    survivorTiles: MergeTile[];
    absorbedTileOptions: MergeTileOption[];
}

export interface PrefLabelCandidate {
    tileId: string;
    content: string;
    isFromSurvivor: boolean;
}

export interface PrefLabelConflict {
    languageCode: string;
    languageLabel: string;
    candidates: PrefLabelCandidate[];
}

export interface MergeRetirementChoice {
    createExactMatchTiles: boolean;
    retireAbsorbedConcept: boolean;
    retirementStrategy: MergeRetirementStrategy;
}

export interface MergeSectionSummary {
    sectionTitle: string;
    selectedCount: number;
}

export interface MergeSelectionState {
    sectionComparisons: SectionComparison[];
    prefLabelConflicts: PrefLabelConflict[];
    prefLabelWinnerByLanguage: Record<string, string>;
    hasUnresolvedPrefLabelConflicts: boolean;
    selectedTileCount: number;
    sectionSummaries: MergeSectionSummary[];
}
