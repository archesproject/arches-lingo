<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { useGettext } from "vue3-gettext";

import MergeComparisonSection from "@/arches_lingo/components/concept/ConceptMerge/components/MergeComparisonSection.vue";
import MergePrefLabelResolver from "@/arches_lingo/components/concept/ConceptMerge/components/MergePrefLabelResolver.vue";

import { MERGE_SECTIONS } from "@/arches_lingo/components/concept/ConceptMerge/constants.ts";
import {
    buildSectionComparison,
    collectReferencedConceptIds,
    extractSectionTiles,
    findPrefLabelConflicts,
} from "@/arches_lingo/components/concept/ConceptMerge/utils.ts";
import { fetchConceptResources } from "@/arches_lingo/api.ts";

import type { Label } from "@/arches_controlled_lists/types.ts";
import type { SearchResultItem } from "@/arches_lingo/types.ts";

import type {
    MergeSection,
    MergeSelectionState,
    SectionComparison,
} from "@/arches_lingo/components/concept/ConceptMerge/types.ts";

const {
    survivorConceptId,
    survivorAliasedData,
    absorbedAliasedData,
    isCrossScheme,
} = defineProps<{
    survivorConceptId: string;
    survivorAliasedData: Record<string, unknown> | undefined;
    absorbedAliasedData: Record<string, unknown> | undefined;
    isCrossScheme: boolean;
}>();

const emit = defineEmits<{
    (event: "update:selectionState", selectionState: MergeSelectionState): void;
}>();

const { $gettext } = useGettext();

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

const sectionComparisons = ref<SectionComparison[]>([]);
const prefLabelWinnerByLanguage = ref<Record<string, string>>({});
const conceptLabelsById = ref<Map<string, Label[]>>(new Map());

// Referenced concepts are named through getItemLabel, so their labels are fetched
// once per comparison. A failure leaves the cards on their display values.
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

// Sections neither concept uses would be empty rows, so they are left out.
function isSectionBlocked(section: MergeSection) {
    return Boolean(isCrossScheme && section.schemeScoped);
}

function buildComparisons() {
    sectionComparisons.value = MERGE_SECTIONS.map((section) =>
        buildSectionComparison(
            section,
            extractSectionTiles(survivorAliasedData, section),
            extractSectionTiles(absorbedAliasedData, section),
            survivorConceptId,
            isSectionBlocked(section),
        ),
    ).filter(
        (comparison) =>
            comparison.survivorTiles.length > 0 ||
            comparison.absorbedTileOptions.length > 0,
    );
}

watch(
    () => [survivorConceptId, survivorAliasedData, absorbedAliasedData],
    () => {
        buildComparisons();
        void loadReferencedConceptLabels();
    },
    { immediate: true },
);

const labelComparison = computed(function () {
    return sectionComparisons.value.find(
        (comparison) =>
            comparison.section.nodegroupAlias === "appellative_status",
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

// A conflict defaults to the label already on the surviving concept, so the
// editor only has to intervene when they want the incoming label to win.
watch(
    prefLabelConflicts,
    function (conflicts) {
        const winners: Record<string, string> = {};
        for (const conflict of conflicts) {
            const existingWinner =
                prefLabelWinnerByLanguage.value[conflict.languageCode];
            const isStillACandidate = conflict.candidates.some(
                (candidate) => candidate.tileId === existingWinner,
            );
            const survivorCandidate = conflict.candidates.find(
                (candidate) => candidate.isFromSurvivor,
            );
            winners[conflict.languageCode] = isStillACandidate
                ? existingWinner
                : (survivorCandidate ?? conflict.candidates[0]).tileId;
        }
        prefLabelWinnerByLanguage.value = winners;
    },
    { immediate: true },
);

const selectedTileCount = computed(function () {
    return sectionComparisons.value
        .flatMap((comparison) => comparison.absorbedTileOptions)
        .filter((option) => option.isSelected).length;
});

const sectionSummaries = computed(function () {
    return sectionComparisons.value
        .map((comparison) => ({
            sectionTitle:
                sectionTitlesByAlias.value[comparison.section.nodegroupAlias],
            selectedCount: comparison.absorbedTileOptions.filter(
                (option) => option.isSelected,
            ).length,
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

watch(selectionState, (state) => emit("update:selectionState", state), {
    immediate: true,
    deep: true,
});

function onSelectionChange(tileId: string, isSelected: boolean) {
    for (const comparison of sectionComparisons.value) {
        for (const option of comparison.absorbedTileOptions) {
            if (option.tile.tileid === tileId) {
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
            @update:winner="onPrefLabelWinnerChange"
        />

        <MergeComparisonSection
            v-for="comparison in sectionComparisons"
            :key="comparison.section.nodegroupAlias"
            :section-title="
                sectionTitlesByAlias[comparison.section.nodegroupAlias]
            "
            :comparison="comparison"
            :concept-labels-by-id="conceptLabelsById"
            :is-blocked="isSectionBlocked(comparison.section)"
            @update:selection="onSelectionChange"
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
