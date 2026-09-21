import { SKOS_PREF_LABEL_URI } from "@/arches_lingo/constants.ts";

import type { AliasedNodeData } from "@/arches_vue_components/types.ts";
import type {
    MergeRequestPayload,
    ResourceInstanceResult,
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

/**
 * The scheme a concept belongs to, however it is attached.
 *
 * A top concept records its scheme on top_concept_of rather than
 * part_of_scheme, so both are read here -- the same fallback the server's
 * resolve_scheme_id makes.
 */
export function resolveSchemeId(
    concept: ResourceInstanceResult | undefined,
): string | undefined {
    const aliasedData = concept?.aliased_data;
    return (
        aliasedData?.part_of_scheme?.aliased_data?.part_of_scheme
            ?.node_value?.[0]?.resourceId ??
        aliasedData?.top_concept_of?.aliased_data?.top_concept_of
            ?.node_value?.[0]?.resourceId
    );
}

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
 * Reduce a node value to a comparable string.
 *
 * Resource-instance and reference values carry per-tile bookkeeping alongside
 * the value itself, so only the identifying part of each entry is kept. This
 * mirrors normalize_node_value in the merge service, so the client and the
 * server agree on when two tiles hold the same value.
 */
export function normalizeNodeValue(nodeValue: unknown): string {
    if (Array.isArray(nodeValue)) {
        return nodeValue
            .map((entry) => {
                if (entry && typeof entry === "object") {
                    const reference = entry as {
                        resourceId?: string;
                        uri?: string;
                    };
                    return reference.resourceId ?? reference.uri ?? "";
                }
                return String(entry);
            })
            .join("|");
    }
    if (nodeValue === null || nodeValue === undefined) {
        return "";
    }
    return String(nodeValue);
}

export function buildTileIdentityKey(
    section: MergeSection,
    tile: MergeTile,
): string | null {
    if (!section.identityNodeAliases) {
        return null;
    }
    return section.identityNodeAliases
        .map((nodeAlias) =>
            normalizeNodeValue(getNodeData(tile, nodeAlias)?.node_value),
        )
        .join("::");
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

// Resource-instance nodes on an absorbed tile that can name the survivor itself.
// Mirrors SELF_REFERENCE_NODES_BY_NODEGROUP in the merge service.
const SELF_REFERENCE_NODE_ALIASES_BY_SECTION: Record<string, string[]> = {
    classification_status: ["classification_status_ascribed_classification"],
    relation_status: ["relation_status_ascribed_comparate"],
};

/**
 * True when a tile says nothing beyond the relationship the merge dissolves.
 *
 * The absorbed concept's broader tile naming only the survivor, or a relation
 * recorded solely between the two, would make the survivor its own parent or its
 * own relative. The server drops these on the way across, so they are not offered
 * here. A tile that names other concepts as well is still worth taking: the
 * server keeps those references and strips only the survivor's.
 */
export function isSelfReferenceOnly(
    section: MergeSection,
    tile: MergeTile,
    survivorConceptId: string,
): boolean {
    const nodeAliases =
        SELF_REFERENCE_NODE_ALIASES_BY_SECTION[section.nodegroupAlias];
    if (!nodeAliases) {
        return false;
    }

    return nodeAliases.some(function (nodeAlias) {
        const referencedIds = getReferencedResourceIds(tile, nodeAlias);
        return (
            referencedIds.length > 0 &&
            referencedIds.every(
                (resourceId) => resourceId === survivorConceptId,
            )
        );
    });
}

export function buildSectionComparison(
    section: MergeSection,
    survivorTiles: MergeTile[],
    absorbedTiles: MergeTile[],
    survivorConceptId: string,
    isBlocked = false,
): SectionComparison {
    const survivorIdentityKeys = new Set(
        survivorTiles
            .map((tile) => buildTileIdentityKey(section, tile))
            .filter(
                (identityKey): identityKey is string => identityKey !== null,
            ),
    );

    const absorbedTileOptions = absorbedTiles
        .filter(
            (tile) => !isSelfReferenceOnly(section, tile, survivorConceptId),
        )
        .map((tile) => {
            const identityKey = buildTileIdentityKey(section, tile);
            const alreadyOnSurvivor =
                identityKey !== null && survivorIdentityKeys.has(identityKey);

            // Taking a cardinality-1 value overwrites what the survivor already
            // has, so it is only selected by default when there is nothing to
            // overwrite. A blocked section is never selected, so the counts, the
            // summary and the payload all agree with the disabled controls.
            const isSelected =
                !isBlocked &&
                (section.cardinality === "n"
                    ? !alreadyOnSurvivor
                    : survivorTiles.length === 0);

            return { tile, identityKey, alreadyOnSurvivor, isSelected };
        });

    return { section, survivorTiles, absorbedTileOptions };
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
        const languageCode = normalizeNodeValue(languageNodeData?.node_value);
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
): MergeRequestPayload {
    // Scheme-scoped sections are disabled in the comparison rather than hidden,
    // so a selection made before the concept was chosen could still be carried
    // here. The server rejects them either way; dropping them means the editor
    // sees the merge they were shown rather than an error.
    const tileSelections = sectionComparisons
        .filter(
            (comparison) => !isCrossScheme || !comparison.section.schemeScoped,
        )
        .flatMap((comparison) => comparison.absorbedTileOptions)
        .filter((option) => option.isSelected && option.tile.tileid)
        .map((option) => option.tile.tileid as string);

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

    return {
        absorbed_concept_id: absorbedConceptId,
        tile_selections: tileSelections,
        pref_label_demotions: prefLabelDemotions,
        survivor_pref_label_demotions: survivorPrefLabelDemotions,
        create_exact_match_tiles: retirement.createExactMatchTiles,
        // Retiring rehomes the concept's children within its own scheme, so a
        // merge across schemes leaves it in place.
        retire_absorbed_concept:
            !isCrossScheme && retirement.retireAbsorbedConcept,
        retirement_strategy:
            !isCrossScheme && retirement.retireAbsorbedConcept
                ? retirement.retirementStrategy
                : null,
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
