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
    // Display nodes holding references to other concepts. Their names come from
    // getItemLabel against fetched labels, not from the tile's display_value,
    // which is the resource descriptor rather than a language-aware label.
    conceptReferenceNodeAliases?: string[];
    // Images are offered one at a time and added to the survivor's own list,
    // rather than the tile replacing the survivor's images wholesale.
    digitalObjectReferenceNodeAliases?: string[];
    isHierarchical?: boolean;
}

export interface MergeTileOption {
    tile: MergeTile;
    alreadyOnSurvivor: boolean;
    isSelected: boolean;
}

export interface MergeDigitalObjectOption {
    digitalObjectId: string;
    alreadyOnSurvivor: boolean;
    isSelected: boolean;
}

export interface SectionComparison {
    section: MergeSection;
    isBlocked: boolean;
    survivorTiles: MergeTile[];
    absorbedTileOptions: MergeTileOption[];
    survivorDigitalObjectIds: string[];
    absorbedDigitalObjectOptions: MergeDigitalObjectOption[];
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
