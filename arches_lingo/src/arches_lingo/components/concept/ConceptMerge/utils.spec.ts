import {
    SKOS_ALT_LABEL_URI,
    SKOS_PREF_LABEL_URI,
} from "@/arches_lingo/constants.ts";
import {
    buildSearchResultFromAncestorPath,
    buildMergePayload,
    buildSectionComparison,
    countSelectedValues,
    collectReferencedConceptIds,
    collectReferencedDigitalObjectIds,
    extractSectionTiles,
    findPrefLabelConflicts,
    getReferencedResourceIds,
} from "@/arches_lingo/components/concept/ConceptMerge/utils.ts";

import type { MergeTileState, SearchResultItem } from "@/arches_lingo/types.ts";
import type {
    MergeSection,
    MergeTile,
} from "@/arches_lingo/components/concept/ConceptMerge/types.ts";

const LABEL_SECTION: MergeSection = {
    nodegroupAlias: "appellative_status",
    cardinality: "n",
    displayNodeAliases: ["appellative_status_ascribed_name_content"],
};

const NO_TILE_STATES: Record<string, MergeTileState> = {};

const TYPE_SECTION: MergeSection = {
    nodegroupAlias: "type",
    cardinality: "1",
    displayNodeAliases: ["type"],
};

function labelTile(
    tileid: string,
    content: string,
    languageCode = "en",
    relationUri = SKOS_PREF_LABEL_URI,
): MergeTile {
    return {
        tileid,
        aliased_data: {
            appellative_status_ascribed_name_content: {
                display_value: content,
                node_value: content,
                details: [],
            },
            appellative_status_ascribed_name_language: {
                display_value: languageCode.toUpperCase(),
                node_value: languageCode,
                details: [],
            },
            appellative_status_ascribed_relation: {
                display_value: "label type",
                node_value: [{ uri: relationUri }],
                details: [],
            },
        },
    };
}

describe("extractSectionTiles", () => {
    it("normalises a cardinality-one nodegroup to a list", () => {
        const tile = labelTile("a", "x");
        expect(extractSectionTiles({ type: tile }, TYPE_SECTION)).toEqual([
            tile,
        ]);
    });

    it("returns an empty list when the nodegroup is absent or null", () => {
        expect(extractSectionTiles({}, TYPE_SECTION)).toEqual([]);
        expect(extractSectionTiles({ type: null }, TYPE_SECTION)).toEqual([]);
        expect(extractSectionTiles(undefined, TYPE_SECTION)).toEqual([]);
    });
});

describe("buildSectionComparison", () => {
    it("pre-unchecks a value the survivor already holds", () => {
        const comparison = buildSectionComparison(
            LABEL_SECTION,
            [labelTile("survivor-1", "Cloth")],
            [
                labelTile("absorbed-1", "Cloth"),
                labelTile("absorbed-2", "Fabric"),
            ],
            { "absorbed-1": "already_on_survivor" },
        );

        const [duplicate, novel] = comparison.absorbedTileOptions;
        expect(duplicate.alreadyOnSurvivor).toBe(true);
        expect(duplicate.isSelected).toBe(false);
        expect(novel.alreadyOnSurvivor).toBe(false);
        expect(novel.isSelected).toBe(true);
    });

    it("leaves a single-value section unselected when it would overwrite", () => {
        const comparison = buildSectionComparison(
            TYPE_SECTION,
            [labelTile("survivor-type", "guide term")],
            [labelTile("absorbed-type", "concept")],
            NO_TILE_STATES,
        );
        expect(comparison.absorbedTileOptions[0].isSelected).toBe(false);
    });

    it("selects a single value when the survivor has nothing to overwrite", () => {
        const comparison = buildSectionComparison(
            TYPE_SECTION,
            [],
            [labelTile("absorbed-type", "concept")],
            NO_TILE_STATES,
        );
        expect(comparison.absorbedTileOptions[0].isSelected).toBe(true);
    });
});

describe("findPrefLabelConflicts", () => {
    it("reports a language with two preferred labels", () => {
        const comparison = buildSectionComparison(
            LABEL_SECTION,
            [labelTile("survivor-1", "Cloth")],
            [labelTile("absorbed-1", "Fabric")],
            NO_TILE_STATES,
        );

        const conflicts = findPrefLabelConflicts(
            comparison.survivorTiles,
            comparison.absorbedTileOptions,
        );

        expect(conflicts).toHaveLength(1);
        expect(conflicts[0].languageCode).toEqual("en");
        expect(conflicts[0].candidates.map((c) => c.tileId)).toEqual([
            "survivor-1",
            "absorbed-1",
        ]);
    });

    it("ignores alternative labels and unselected candidates", () => {
        const altLabelComparison = buildSectionComparison(
            LABEL_SECTION,
            [labelTile("survivor-1", "Cloth")],
            [labelTile("absorbed-1", "Fabric", "en", SKOS_ALT_LABEL_URI)],
            NO_TILE_STATES,
        );
        expect(
            findPrefLabelConflicts(
                altLabelComparison.survivorTiles,
                altLabelComparison.absorbedTileOptions,
            ),
        ).toEqual([]);

        const deselectedComparison = buildSectionComparison(
            LABEL_SECTION,
            [labelTile("survivor-1", "Cloth")],
            [labelTile("absorbed-1", "Fabric")],
            NO_TILE_STATES,
        );
        deselectedComparison.absorbedTileOptions[0].isSelected = false;
        expect(
            findPrefLabelConflicts(
                deselectedComparison.survivorTiles,
                deselectedComparison.absorbedTileOptions,
            ),
        ).toEqual([]);
    });

    it("does not report languages with a single preferred label", () => {
        const comparison = buildSectionComparison(
            LABEL_SECTION,
            [labelTile("survivor-1", "Cloth", "en")],
            [labelTile("absorbed-1", "Tissu", "fr")],
            NO_TILE_STATES,
        );
        expect(
            findPrefLabelConflicts(
                comparison.survivorTiles,
                comparison.absorbedTileOptions,
            ),
        ).toEqual([]);
    });
});

describe("buildMergePayload", () => {
    it("collects selected tiles and demotes every losing preferred label", () => {
        const comparison = buildSectionComparison(
            LABEL_SECTION,
            [labelTile("survivor-1", "Cloth")],
            [
                labelTile("absorbed-1", "Fabric"),
                labelTile("absorbed-2", "Weave"),
            ],
            NO_TILE_STATES,
        );
        const conflicts = findPrefLabelConflicts(
            comparison.survivorTiles,
            comparison.absorbedTileOptions,
        );

        const payload = buildMergePayload(
            "absorbed-concept",
            [comparison],
            conflicts,
            { en: "absorbed-1" },
            {
                createExactMatchTiles: true,
                retireAbsorbedConcept: true,
                retirementStrategy: "reparent_to_survivor",
            },
        );

        expect(payload.absorbed_concept_id).toEqual("absorbed-concept");
        expect(payload.tile_selections).toEqual(["absorbed-1", "absorbed-2"]);
        expect(payload.survivor_pref_label_demotions).toEqual(["survivor-1"]);
        expect(payload.pref_label_demotions).toEqual(["absorbed-2"]);
        expect(payload.create_exact_match_tiles).toBe(true);
        expect(payload.retire_absorbed_concept).toBe(true);
        expect(payload.retirement_strategy).toEqual("reparent_to_survivor");
    });

    it("drops scheme-scoped selections and retirement across schemes", () => {
        const labelComparison = buildSectionComparison(
            LABEL_SECTION,
            [],
            [labelTile("absorbed-1", "Fabric")],
            NO_TILE_STATES,
        );
        const broaderComparison = buildSectionComparison(
            BROADER_SECTION,
            [],
            [broaderTile("absorbed-broader", "some-other-concept")],
            NO_TILE_STATES,
            true,
        );

        const payload = buildMergePayload(
            "absorbed-concept",
            [labelComparison, broaderComparison],
            [],
            {},
            {
                createExactMatchTiles: true,
                retireAbsorbedConcept: true,
                retirementStrategy: "reparent_to_survivor",
            },
            true,
        );

        expect(payload.tile_selections).toEqual(["absorbed-1"]);
        expect(payload.retire_absorbed_concept).toBe(false);
        expect(payload.retirement_strategy).toBeNull();
        // The link between the two records is the point of a cross-scheme merge.
        expect(payload.create_exact_match_tiles).toBe(true);
    });

    it("keeps scheme-scoped selections and retirement within one scheme", () => {
        const broaderComparison = buildSectionComparison(
            BROADER_SECTION,
            [],
            [broaderTile("absorbed-broader", "some-other-concept")],
            NO_TILE_STATES,
        );
        broaderComparison.absorbedTileOptions[0].isSelected = true;

        const payload = buildMergePayload(
            "absorbed-concept",
            [broaderComparison],
            [],
            {},
            {
                createExactMatchTiles: true,
                retireAbsorbedConcept: true,
                retirementStrategy: "reparent_to_survivor",
            },
        );

        expect(payload.tile_selections).toEqual(["absorbed-broader"]);
        expect(payload.retire_absorbed_concept).toBe(true);
    });

    it("demotes nothing when the surviving label keeps the language", () => {
        const comparison = buildSectionComparison(
            LABEL_SECTION,
            [labelTile("survivor-1", "Cloth")],
            [labelTile("absorbed-1", "Fabric")],
            NO_TILE_STATES,
        );
        const conflicts = findPrefLabelConflicts(
            comparison.survivorTiles,
            comparison.absorbedTileOptions,
        );

        const payload = buildMergePayload(
            "absorbed-concept",
            [comparison],
            conflicts,
            { en: "survivor-1" },
            {
                createExactMatchTiles: false,
                retireAbsorbedConcept: false,
                retirementStrategy: "reparent_to_survivor",
            },
        );

        expect(payload.survivor_pref_label_demotions).toEqual([]);
        expect(payload.pref_label_demotions).toEqual(["absorbed-1"]);
        expect(payload.create_exact_match_tiles).toBe(false);
    });

    it("sends no retirement strategy when the concept is not being retired", () => {
        const comparison = buildSectionComparison(
            LABEL_SECTION,
            [],
            [labelTile("absorbed-1", "Fabric")],
            NO_TILE_STATES,
        );

        const payload = buildMergePayload(
            "absorbed-concept",
            [comparison],
            [],
            {},
            {
                createExactMatchTiles: true,
                retireAbsorbedConcept: false,
                retirementStrategy: "reparent_to_survivor",
            },
        );

        expect(payload.retire_absorbed_concept).toBe(false);
        expect(payload.retirement_strategy).toBeNull();
    });
});

const BROADER_SECTION: MergeSection = {
    nodegroupAlias: "classification_status",
    cardinality: "n",
    displayNodeAliases: ["classification_status_ascribed_classification"],
    conceptReferenceNodeAliases: [
        "classification_status_ascribed_classification",
    ],
    isHierarchical: true,
};

function broaderTile(tileid: string, ...parentIds: string[]): MergeTile {
    return {
        tileid,
        aliased_data: {
            classification_status_ascribed_classification: {
                display_value: "some descriptor",
                node_value: parentIds.map((resourceId) => ({ resourceId })),
                details: [],
            },
        },
    };
}

describe("buildSectionComparison with the server's tile states", () => {
    it("leaves out a tile the merge would drop", () => {
        const comparison = buildSectionComparison(
            BROADER_SECTION,
            [],
            [
                broaderTile("dropped-broader", "survivor-descendant"),
                broaderTile("kept-broader", "other-parent"),
            ],
            { "dropped-broader": "dropped", "kept-broader": "selectable" },
        );

        expect(
            comparison.absorbedTileOptions.map((option) => option.tile.tileid),
        ).toEqual(["kept-broader"]);
    });

    it("offers a broader tile without selecting it", () => {
        const comparison = buildSectionComparison(
            BROADER_SECTION,
            [],
            [broaderTile("absorbed-broader", "other-parent")],
            NO_TILE_STATES,
        );

        expect(comparison.absorbedTileOptions).toHaveLength(1);
        expect(comparison.absorbedTileOptions[0].isSelected).toBe(false);
    });

    it("leaves a single value the survivor already holds unselected", () => {
        const comparison = buildSectionComparison(
            TYPE_SECTION,
            [],
            [labelTile("absorbed-type", "concept")],
            { "absorbed-type": "already_on_survivor" },
        );

        expect(comparison.absorbedTileOptions[0].alreadyOnSurvivor).toBe(true);
        expect(comparison.absorbedTileOptions[0].isSelected).toBe(false);
    });
});

describe("buildSearchResultFromAncestorPath", () => {
    it("puts the concept first with everything above it as its lineage", () => {
        const ancestorPath = ["scheme", "parent", "concept"].map(
            (id) => ({ id, labels: [] }) as unknown as SearchResultItem,
        );

        const searchResult = buildSearchResultFromAncestorPath(ancestorPath);

        expect(searchResult?.id).toEqual("concept");
        expect(searchResult?.parents[0].map((pathItem) => pathItem.id)).toEqual(
            ["scheme", "parent"],
        );
    });

    it("returns nothing for an empty path", () => {
        expect(buildSearchResultFromAncestorPath([])).toBeUndefined();
    });
});

describe("getReferencedResourceIds", () => {
    it("pulls resource ids out of a reference node", () => {
        expect(
            getReferencedResourceIds(
                broaderTile("a", "parent-1", "parent-2"),
                "classification_status_ascribed_classification",
            ),
        ).toEqual(["parent-1", "parent-2"]);
    });

    it("returns nothing for a node that holds no references", () => {
        expect(
            getReferencedResourceIds(labelTile("a", "Cloth"), "missing_alias"),
        ).toEqual([]);
    });
});

describe("collectReferencedConceptIds", () => {
    it("gathers ids from both sides without duplicates", () => {
        const comparison = buildSectionComparison(
            BROADER_SECTION,
            [broaderTile("survivor-1", "shared-parent")],
            [broaderTile("absorbed-1", "shared-parent", "other-parent")],
            NO_TILE_STATES,
        );

        expect(collectReferencedConceptIds([comparison]).sort()).toEqual([
            "other-parent",
            "shared-parent",
        ]);
    });

    it("ignores sections that hold no concept references", () => {
        const comparison = buildSectionComparison(
            LABEL_SECTION,
            [labelTile("survivor-1", "Cloth")],
            [labelTile("absorbed-1", "Fabric")],
            NO_TILE_STATES,
        );
        expect(collectReferencedConceptIds([comparison])).toEqual([]);
    });
});

const IMAGES_SECTION: MergeSection = {
    nodegroupAlias: "depicting_digital_asset_internal",
    cardinality: "1",
    displayNodeAliases: ["depicting_digital_asset_internal"],
    digitalObjectReferenceNodeAliases: ["depicting_digital_asset_internal"],
};

function imagesTile(tileid: string, ...digitalObjectIds: string[]): MergeTile {
    return {
        tileid,
        aliased_data: {
            depicting_digital_asset_internal: {
                display_value: "",
                node_value: digitalObjectIds.map((resourceId) => ({
                    resourceId,
                })),
                details: [],
            },
        },
    };
}

describe("collectReferencedDigitalObjectIds", () => {
    it("gathers ids from both sides without duplicates", () => {
        const comparison = buildSectionComparison(
            IMAGES_SECTION,
            [imagesTile("survivor-1", "shared-image")],
            [imagesTile("absorbed-1", "shared-image", "other-image")],
            NO_TILE_STATES,
        );

        expect(collectReferencedDigitalObjectIds([comparison]).sort()).toEqual([
            "other-image",
            "shared-image",
        ]);
    });

    it("ignores concept references", () => {
        const comparison = buildSectionComparison(
            BROADER_SECTION,
            [broaderTile("survivor-1", "parent")],
            [],
            NO_TILE_STATES,
        );
        expect(collectReferencedDigitalObjectIds([comparison])).toEqual([]);
    });
});

describe("buildSectionComparison for images", () => {
    it("offers each absorbed image on its own rather than the whole tile", () => {
        const comparison = buildSectionComparison(
            IMAGES_SECTION,
            [imagesTile("survivor-1", "shared-image")],
            [imagesTile("absorbed-1", "shared-image", "other-image")],
            NO_TILE_STATES,
        );

        expect(comparison.survivorTiles).toEqual([]);
        expect(comparison.absorbedTileOptions).toEqual([]);
        expect(comparison.survivorDigitalObjectIds).toEqual(["shared-image"]);
        expect(comparison.absorbedDigitalObjectOptions).toEqual([
            {
                digitalObjectId: "shared-image",
                alreadyOnSurvivor: true,
                isSelected: false,
            },
            {
                digitalObjectId: "other-image",
                alreadyOnSurvivor: false,
                isSelected: true,
            },
        ]);
        expect(countSelectedValues(comparison)).toBe(1);
    });

    it("selects nothing in a blocked section", () => {
        const comparison = buildSectionComparison(
            IMAGES_SECTION,
            [],
            [imagesTile("absorbed-1", "other-image")],
            NO_TILE_STATES,
            true,
        );
        expect(countSelectedValues(comparison)).toBe(0);
    });

    it("sends selected images separately from selected tiles", () => {
        const imageComparison = buildSectionComparison(
            IMAGES_SECTION,
            [imagesTile("survivor-1", "shared-image")],
            [imagesTile("absorbed-1", "shared-image", "other-image")],
            NO_TILE_STATES,
        );
        const labelComparison = buildSectionComparison(
            LABEL_SECTION,
            [],
            [labelTile("absorbed-label", "Fabric")],
            NO_TILE_STATES,
        );

        const payload = buildMergePayload(
            "absorbed-concept",
            [imageComparison, labelComparison],
            [],
            {},
            {
                createExactMatchTiles: true,
                retireAbsorbedConcept: false,
                retirementStrategy: "reparent_to_survivor",
            },
        );

        expect(payload.tile_selections).toEqual(["absorbed-label"]);
        expect(payload.digital_object_selections).toEqual(["other-image"]);
    });
});
