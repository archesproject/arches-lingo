<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { useGettext } from "vue3-gettext";

import MergeComparisonSection from "@/arches_lingo/components/concept/ConceptMerge/components/MergeComparisonSection.vue";
import MergePrefLabelResolver from "@/arches_lingo/components/concept/ConceptMerge/components/MergePrefLabelResolver.vue";

import { MERGE_SECTIONS } from "@/arches_lingo/components/concept/ConceptMerge/constants.ts";
import {
    buildSectionComparison,
    collectReferencedConceptIds,
    collectReferencedDigitalObjectIds,
    countSelectedValues,
    extractSectionTiles,
    findPrefLabelConflicts,
} from "@/arches_lingo/components/concept/ConceptMerge/utils.ts";
import { DIGITAL_OBJECT_GRAPH_SLUG } from "@/arches_lingo/components/concept/ConceptImages/components/constants.ts";
import {
    fetchConceptResources,
    fetchLingoResourcesBatch,
} from "@/arches_lingo/api.ts";

import type { Label } from "@/arches_controlled_lists/types.ts";
import type {
    ConceptMergePreview,
    DigitalObjectInstance,
    SearchResultItem,
} from "@/arches_lingo/types.ts";
import type {
    MergeSelectionState,
    PrefLabelCandidate,
    SectionComparison,
} from "@/arches_lingo/components/concept/ConceptMerge/types.ts";

const LABEL_SECTION_ALIAS = "appellative_status";

const {
    survivorAliasedData,
    absorbedAliasedData,
    survivorLabel,
    absorbedLabel,
    mergePreview,
} = defineProps<{
    survivorAliasedData: Record<string, unknown> | undefined;
    absorbedAliasedData: Record<string, unknown> | undefined;
    survivorLabel: string | undefined;
    absorbedLabel: string | undefined;
    mergePreview: ConceptMergePreview;
}>();

const emit = defineEmits<{
    (event: "update:selectionState", selectionState: MergeSelectionState): void;
}>();

const { $gettext } = useGettext();

const sectionComparisons = ref<SectionComparison[]>([]);
const prefLabelWinnerByLanguage = ref<Record<string, string>>({});
const conceptLabelsById = ref<Map<string, Label[]>>(new Map());
const digitalObjectsById = ref<Map<string, DigitalObjectInstance>>(new Map());

const sectionTitlesByAlias = computed<Record<string, string>>(function () {
    return {
        appellative_status: $gettext("Concept Labels"),
        statement: $gettext("Concept Notes"),
        classification_status: $gettext("Hierarchical Position"),
        top_concept_of: $gettext("Top Concept Of"),
        relation_status: $gettext("Associated Concepts"),
        match_status: $gettext("Matched Concepts"),
        type: $gettext("Concept Type"),
        depicting_digital_asset_internal: $gettext("Concept Images"),
        depicting_digital_asset_external: $gettext("External Image"),
        also_instance_of: $gettext("Also Instance Of"),
        status: $gettext("Status"),
        creation: $gettext("Creation"),
    };
});

const labelComparison = computed(function () {
    return sectionComparisons.value.find(
        (comparison) =>
            comparison.section.nodegroupAlias === LABEL_SECTION_ALIAS,
    );
});

const prefLabelConflicts = computed(function () {
    if (!labelComparison.value) {
        return [];
    }
    return findPrefLabelConflicts(
        labelComparison.value.survivorTiles,
        labelComparison.value.absorbedTileOptions,
    );
});

const selectedTileCount = computed(function () {
    return sectionComparisons.value.reduce(
        (total, comparison) => total + countSelectedValues(comparison),
        0,
    );
});

const sectionSummaries = computed(function () {
    return sectionComparisons.value
        .map((comparison) => ({
            sectionTitle:
                sectionTitlesByAlias.value[comparison.section.nodegroupAlias],
            selectedCount: countSelectedValues(comparison),
        }))
        .filter((summary) => summary.selectedCount > 0);
});

const selectionState = computed<MergeSelectionState>(function () {
    return {
        sectionComparisons: sectionComparisons.value,
        prefLabelConflicts: prefLabelConflicts.value,
        prefLabelWinnerByLanguage: prefLabelWinnerByLanguage.value,
        hasUnresolvedPrefLabelConflicts: prefLabelConflicts.value.some(
            (conflict) =>
                !prefLabelWinnerByLanguage.value[conflict.languageCode],
        ),
        selectedTileCount: selectedTileCount.value,
        sectionSummaries: sectionSummaries.value,
    };
});

watch(
    () => [survivorAliasedData, absorbedAliasedData, mergePreview],
    function () {
        buildComparisons();
        void loadReferencedConceptLabels();
        void loadReferencedDigitalObjects();
    },
    { immediate: true },
);

// A conflict defaults to the label already on the surviving concept, so the
// editor only has to intervene when they want the incoming label to win.
watch(
    prefLabelConflicts,
    function (conflicts) {
        const winners: Record<string, string> = {};
        for (const conflict of conflicts) {
            winners[conflict.languageCode] = chooseDefaultWinner(
                conflict.languageCode,
                conflict.candidates,
            );
        }
        prefLabelWinnerByLanguage.value = winners;
    },
    { immediate: true },
);

watch(selectionState, (state) => emit("update:selectionState", state), {
    immediate: true,
    deep: true,
});

function chooseDefaultWinner(
    languageCode: string,
    candidates: PrefLabelCandidate[],
) {
    const existingWinner = prefLabelWinnerByLanguage.value[languageCode];
    if (candidates.some((candidate) => candidate.tileId === existingWinner)) {
        return existingWinner;
    }
    const survivorCandidate = candidates.find(
        (candidate) => candidate.isFromSurvivor,
    );
    return (survivorCandidate ?? candidates[0]).tileId;
}

function isSectionBlocked(nodegroupAlias: string) {
    return mergePreview.blocked_nodegroup_aliases.includes(nodegroupAlias);
}

// Sections neither concept uses would be empty rows, so they are left out.
function buildComparisons() {
    sectionComparisons.value = MERGE_SECTIONS.map((section) =>
        buildSectionComparison(
            section,
            extractSectionTiles(survivorAliasedData, section),
            extractSectionTiles(absorbedAliasedData, section),
            mergePreview.tile_states,
            isSectionBlocked(section.nodegroupAlias),
        ),
    ).filter(
        (comparison) =>
            comparison.survivorTiles.length > 0 ||
            comparison.absorbedTileOptions.length > 0 ||
            comparison.survivorDigitalObjectIds.length > 0 ||
            comparison.absorbedDigitalObjectOptions.length > 0,
    );
}

// A failure leaves the cards on their display values.
async function loadReferencedConceptLabels() {
    const conceptIds = collectReferencedConceptIds(sectionComparisons.value);
    if (!conceptIds.length) {
        conceptLabelsById.value = new Map();
        return;
    }

    try {
        const parsedResponse = await fetchConceptResources(
            "",
            conceptIds.length,
            1,
            undefined,
            undefined,
            conceptIds,
        );
        conceptLabelsById.value = new Map(
            parsedResponse.data.map((concept: SearchResultItem) => [
                concept.id,
                concept.labels,
            ]),
        );
    } catch {
        conceptLabelsById.value = new Map();
    }
}

// A failure leaves the cards on placeholders.
async function loadReferencedDigitalObjects() {
    const digitalObjectIds = collectReferencedDigitalObjectIds(
        sectionComparisons.value,
    );
    if (!digitalObjectIds.length) {
        digitalObjectsById.value = new Map();
        return;
    }

    try {
        const digitalObjects: DigitalObjectInstance[] =
            await fetchLingoResourcesBatch(
                DIGITAL_OBJECT_GRAPH_SLUG,
                digitalObjectIds,
            );
        digitalObjectsById.value = new Map(
            digitalObjects.map((digitalObject) => [
                digitalObject.resourceinstanceid,
                digitalObject,
            ]),
        );
    } catch {
        digitalObjectsById.value = new Map();
    }
}

function onSelectionChange(tileId: string, isSelected: boolean) {
    for (const comparison of sectionComparisons.value) {
        for (const option of comparison.absorbedTileOptions) {
            if (option.tile.tileid === tileId) {
                option.isSelected = isSelected;
            }
        }
    }
}

function onDigitalObjectSelectionChange(
    digitalObjectId: string,
    isSelected: boolean,
) {
    for (const comparison of sectionComparisons.value) {
        for (const option of comparison.absorbedDigitalObjectOptions) {
            if (option.digitalObjectId === digitalObjectId) {
                option.isSelected = isSelected;
            }
        }
    }
}

function onPrefLabelWinnerChange(languageCode: string, tileId: string) {
    prefLabelWinnerByLanguage.value = {
        ...prefLabelWinnerByLanguage.value,
        [languageCode]: tileId,
    };
}
</script>

<template>
    <div class="merge-comparison">
        <MergePrefLabelResolver
            :conflicts="prefLabelConflicts"
            :winner-by-language="prefLabelWinnerByLanguage"
            :survivor-label="survivorLabel"
            :absorbed-label="absorbedLabel"
            @update:winner="onPrefLabelWinnerChange"
        />

        <MergeComparisonSection
            v-for="comparison in sectionComparisons"
            :key="comparison.section.nodegroupAlias"
            :section-title="
                sectionTitlesByAlias[comparison.section.nodegroupAlias]
            "
            :comparison="comparison"
            :survivor-label="survivorLabel"
            :absorbed-label="absorbedLabel"
            :concept-labels-by-id="conceptLabelsById"
            :digital-objects-by-id="digitalObjectsById"
            @update:selection="onSelectionChange"
            @update:digital-object-selection="onDigitalObjectSelectionChange"
        />
    </div>
</template>

<style scoped>
.merge-comparison {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
</style>
