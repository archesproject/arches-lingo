import { SKOS_PREF_LABEL_URI } from "@/arches_lingo/constants.ts";
import {
    TILE_STATE_ALREADY_ON_SURVIVOR,
    TILE_STATE_DROPPED,
} from "@/arches_lingo/components/concept/ConceptMerge/constants.ts";

import type { AliasedNodeData } from "@/arches_vue_components/types.ts";
import type {
    MergeRequestPayload,
    MergeRetirementStrategy,
    MergeTileState,
    SearchResultItem,
} from "@/arches_lingo/types.ts";
import type {
    MergeRetirementChoice,
    MergeSection,
    MergeTile,
    MergeTileOption,
    PrefLabelCandidate,
    PrefLabelConflict,
    SectionComparison,
} from "@/arches_lingo/components/concept/ConceptMerge/types.ts";

const LABEL_CONTENT_ALIAS = "appellative_status_ascribed_name_content";
const LABEL_LANGUAGE_ALIAS = "appellative_status_ascribed_name_language";
const LABEL_RELATION_ALIAS = "appellative_status_ascribed_relation";

export function getNodeData(
    tile: MergeTile,
    nodeAlias: string,
): AliasedNodeData | undefined {
    return tile.aliased_data?.[nodeAlias];
}

export function getDisplayValue(tile: MergeTile, nodeAlias: string): string {
    return getNodeData(tile, nodeAlias)?.display_value ?? "";
}

/**
 * Read one section's tiles off a resource's aliased data.
 *
 * Cardinality-1 nodegroups arrive as a single object (or null) rather than an
 * array, so both shapes are normalised to a list here.
 */
export function extractSectionTiles(
    aliasedData: Record<string, unknown> | undefined,
    section: MergeSection,
): MergeTile[] {
    const sectionData = aliasedData?.[section.nodegroupAlias];
    if (!sectionData) {
        return [];
    }
    if (Array.isArray(sectionData)) {
        return sectionData as MergeTile[];
    }
    return [sectionData as MergeTile];
}

export function getReferencedResourceIds(
    tile: MergeTile,
    nodeAlias: string,
): string[] {
    const nodeValue = getNodeData(tile, nodeAlias)?.node_value;
    if (!Array.isArray(nodeValue)) {
        return [];
    }
    return nodeValue
        .map((entry) => (entry as { resourceId?: string })?.resourceId)
        .filter((resourceId): resourceId is string => Boolean(resourceId));
}

function getReferencedDigitalObjectIds(
    section: MergeSection,
    tiles: MergeTile[],
): string[] {
    const nodeAliases = section.digitalObjectReferenceNodeAliases ?? [];
    const digitalObjectIds = tiles.flatMap((tile) =>
        nodeAliases.flatMap((nodeAlias) =>
            getReferencedResourceIds(tile, nodeAlias),
        ),
    );
    return [...new Set(digitalObjectIds)];
}

/**
 * Compare an image section by its digital objects rather than its tile.
 *
 * Every image a concept has sits on one tile, so the tile lists are left empty
 * and each image is offered on its own, to be added to the survivor's images
 * rather than replacing them.
 */
function buildDigitalObjectSectionComparison(
    section: MergeSection,
    survivorTiles: MergeTile[],
    absorbedTiles: MergeTile[],
    isBlocked: boolean,
): SectionComparison {
    const survivorDigitalObjectIds = getReferencedDigitalObjectIds(
        section,
        survivorTiles,
    );

    const absorbedDigitalObjectOptions = getReferencedDigitalObjectIds(
        section,
        absorbedTiles,
    ).map((digitalObjectId) => {
        const alreadyOnSurvivor =
            survivorDigitalObjectIds.includes(digitalObjectId);
        return {
            digitalObjectId,
            alreadyOnSurvivor,
            isSelected: !isBlocked && !alreadyOnSurvivor,
        };
    });

    return {
        section,
        isBlocked,
        survivorTiles: [],
        absorbedTileOptions: [],
        survivorDigitalObjectIds,
        absorbedDigitalObjectOptions,
    };
}

// Taking a single value overwrites what the survivor already has, so it is only
// selected when there is nothing to overwrite. Hierarchy sections would move the
// survivor, so they wait for the editor to opt in.
function isSelectedByDefault(
    section: MergeSection,
    survivorTiles: MergeTile[],
    alreadyOnSurvivor: boolean,
    isBlocked: boolean,
): boolean {
    if (isBlocked || alreadyOnSurvivor || section.isHierarchical) {
        return false;
    }
    if (section.cardinality === "n") {
        return true;
    }
    return survivorTiles.length === 0;
}

/**
 * Pair one section's tiles from both concepts, using the server's preview to
 * know which absorbed tiles the survivor already holds and which the merge
 * would drop because they only name the survivor or something beneath it.
 */
export function buildSectionComparison(
    section: MergeSection,
    survivorTiles: MergeTile[],
    absorbedTiles: MergeTile[],
    tileStates: Record<string, MergeTileState>,
    isBlocked = false,
): SectionComparison {
    if (section.digitalObjectReferenceNodeAliases) {
        return buildDigitalObjectSectionComparison(
            section,
            survivorTiles,
            absorbedTiles,
            isBlocked,
        );
    }

    const absorbedTileOptions = absorbedTiles
        .filter((tile) => tileStates[tile.tileid ?? ""] !== TILE_STATE_DROPPED)
        .map(function (tile) {
            const alreadyOnSurvivor =
                tileStates[tile.tileid ?? ""] ===
                TILE_STATE_ALREADY_ON_SURVIVOR;
            return {
                tile,
                alreadyOnSurvivor,
                isSelected: isSelectedByDefault(
                    section,
                    survivorTiles,
                    alreadyOnSurvivor,
                    isBlocked,
                ),
            };
        });

    return {
        section,
        isBlocked,
        survivorTiles,
        absorbedTileOptions,
        survivorDigitalObjectIds: [],
        absorbedDigitalObjectOptions: [],
    };
}

export function countSelectedValues(comparison: SectionComparison): number {
    return [
        ...comparison.absorbedTileOptions,
        ...comparison.absorbedDigitalObjectOptions,
    ].filter((option) => option.isSelected).length;
}

function isPrefLabel(tile: MergeTile): boolean {
    const relationValue = getNodeData(tile, LABEL_RELATION_ALIAS)?.node_value;
    if (!Array.isArray(relationValue)) {
        return false;
    }
    return relationValue.some(
        (reference) =>
            (reference as { uri?: string })?.uri === SKOS_PREF_LABEL_URI,
    );
}

function toPrefLabelCandidate(
    tile: MergeTile,
    isFromSurvivor: boolean,
): PrefLabelCandidate | null {
    if (!tile.tileid) {
        return null;
    }
    return {
        tileId: tile.tileid,
        content: getDisplayValue(tile, LABEL_CONTENT_ALIAS),
        isFromSurvivor,
    };
}

/**
 * Find languages that would end up with more than one preferred label.
 *
 * Only selected absorbed labels count, so unchecking a label resolves its
 * conflict. A language with a single preferred label is never returned.
 */
export function findPrefLabelConflicts(
    survivorTiles: MergeTile[],
    absorbedTileOptions: MergeTileOption[],
): PrefLabelConflict[] {
    const candidatesByLanguage = new Map<
        string,
        { languageLabel: string; candidates: PrefLabelCandidate[] }
    >();

    function collect(tile: MergeTile, isFromSurvivor: boolean) {
        if (!isPrefLabel(tile)) {
            return;
        }
        const candidate = toPrefLabelCandidate(tile, isFromSurvivor);
        if (!candidate) {
            return;
        }
        const languageNodeData = getNodeData(tile, LABEL_LANGUAGE_ALIAS);
        const languageCode = String(languageNodeData?.node_value ?? "");
        if (!languageCode) {
            return;
        }
        const existing = candidatesByLanguage.get(languageCode);
        if (existing) {
            existing.candidates.push(candidate);
        } else {
            candidatesByLanguage.set(languageCode, {
                languageLabel: languageNodeData?.display_value || languageCode,
                candidates: [candidate],
            });
        }
    }

    survivorTiles.forEach((tile) => collect(tile, true));
    absorbedTileOptions
        .filter((option) => option.isSelected)
        .forEach((option) => collect(option.tile, false));

    return [...candidatesByLanguage.entries()]
        .filter(([, entry]) => entry.candidates.length > 1)
        .map(([languageCode, entry]) => ({
            languageCode,
            languageLabel: entry.languageLabel,
            candidates: entry.candidates,
        }));
}

export function buildMergePayload(
    absorbedConceptId: string,
    sectionComparisons: SectionComparison[],
    prefLabelConflicts: PrefLabelConflict[],
    prefLabelWinnerByLanguage: Record<string, string>,
    retirement: MergeRetirementChoice,
    isCrossScheme = false,
    isAbsorbedDraft = false,
): MergeRequestPayload {
    const selectableComparisons = sectionComparisons.filter(
        (comparison) => !comparison.isBlocked,
    );
    const tileSelections = selectableComparisons
        .flatMap((comparison) => comparison.absorbedTileOptions)
        .filter((option) => option.isSelected && option.tile.tileid)
        .map((option) => option.tile.tileid as string);
    const digitalObjectSelections = selectableComparisons
        .flatMap((comparison) => comparison.absorbedDigitalObjectOptions)
        .filter((option) => option.isSelected)
        .map((option) => option.digitalObjectId);

    const prefLabelDemotions: string[] = [];
    const survivorPrefLabelDemotions: string[] = [];

    for (const conflict of prefLabelConflicts) {
        const winnerTileId = prefLabelWinnerByLanguage[conflict.languageCode];
        for (const candidate of conflict.candidates) {
            if (candidate.tileId === winnerTileId) {
                continue;
            }
            if (candidate.isFromSurvivor) {
                survivorPrefLabelDemotions.push(candidate.tileId);
            } else {
                prefLabelDemotions.push(candidate.tileId);
            }
        }
    }

    // A merge across schemes never removes the absorbed concept. Within a scheme
    // a draft is deleted rather than retired, and has no URI to match against.
    const shouldRemove = !isCrossScheme && retirement.removeAbsorbedConcept;
    let retirementStrategy: MergeRetirementStrategy | null = null;
    if (shouldRemove) {
        retirementStrategy = retirement.retirementStrategy;
    }

    return {
        absorbed_concept_id: absorbedConceptId,
        tile_selections: tileSelections,
        digital_object_selections: digitalObjectSelections,
        pref_label_demotions: prefLabelDemotions,
        survivor_pref_label_demotions: survivorPrefLabelDemotions,
        create_exact_match_tiles:
            retirement.createExactMatchTiles && !isAbsorbedDraft,
        retire_absorbed_concept: shouldRemove && !isAbsorbedDraft,
        delete_absorbed_concept: shouldRemove && isAbsorbedDraft,
        retirement_strategy: retirementStrategy,
    };
}

/**
 * Every concept referenced by a comparison's tiles, on either side.
 *
 * Their labels are fetched once so the cards can name them the way the rest of
 * the application does, rather than falling back to a resource descriptor.
 */
export function collectReferencedConceptIds(
    sectionComparisons: SectionComparison[],
): string[] {
    const conceptIds = new Set<string>();

    for (const comparison of sectionComparisons) {
        const referenceAliases =
            comparison.section.conceptReferenceNodeAliases ?? [];
        if (!referenceAliases.length) {
            continue;
        }

        const tiles = [
            ...comparison.survivorTiles,
            ...comparison.absorbedTileOptions.map((option) => option.tile),
        ];
        for (const tile of tiles) {
            for (const nodeAlias of referenceAliases) {
                for (const resourceId of getReferencedResourceIds(
                    tile,
                    nodeAlias,
                )) {
                    conceptIds.add(resourceId);
                }
            }
        }
    }

    return [...conceptIds];
}

/**
 * Every digital object on either side of a comparison.
 *
 * An image tile holds only references, so the objects are fetched once for the
 * cards to show each one's thumbnail, name and description.
 */
export function collectReferencedDigitalObjectIds(
    sectionComparisons: SectionComparison[],
): string[] {
    const digitalObjectIds = sectionComparisons.flatMap((comparison) => [
        ...comparison.survivorDigitalObjectIds,
        ...comparison.absorbedDigitalObjectOptions.map(
            (option) => option.digitalObjectId,
        ),
    ]);
    return [...new Set(digitalObjectIds)];
}

/**
 * Shape an ancestor path (scheme first, the concept itself last) the way a
 * search result carries its concept, so it renders like one.
 */
export function buildSearchResultFromAncestorPath(
    ancestorPath: SearchResultItem[],
): SearchResultItem | undefined {
    const concept = ancestorPath.at(-1);
    if (!concept) {
        return undefined;
    }
    return { ...concept, parents: [ancestorPath.slice(0, -1)] };
}
