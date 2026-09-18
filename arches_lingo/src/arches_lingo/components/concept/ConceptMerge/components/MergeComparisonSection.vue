<script setup lang="ts">
import { computed } from "vue";

import { useGettext } from "vue3-gettext";
import Checkbox from "primevue/checkbox";
import RadioButton from "primevue/radiobutton";
import Tag from "primevue/tag";

import MergeTileCard from "@/arches_lingo/components/concept/ConceptMerge/components/MergeTileCard.vue";

import type { Label } from "@/arches_controlled_lists/types.ts";
import type { SectionComparison } from "@/arches_lingo/components/concept/ConceptMerge/types.ts";

const { sectionTitle, comparison } = defineProps<{
    sectionTitle: string;
    comparison: SectionComparison;
    conceptLabelsById: Map<string, Label[]>;
}>();

const emit = defineEmits<{
    (event: "update:selection", tileId: string, isSelected: boolean): void;
}>();

const { $gettext } = useGettext();

const isSingleValueSection = computed(function () {
    return comparison.section.cardinality === "1";
});

// A single-value section replaces rather than appends, so it is presented as a
// choice between the two sides instead of a per-tile checkbox.
const replacesSurvivorValue = computed(function () {
    return isSingleValueSection.value && comparison.survivorTiles.length > 0;
});

const singleValueTileId = computed(function () {
    return comparison.absorbedTileOptions[0]?.tile.tileid ?? "";
});

const isSurvivorValueKept = computed(function () {
    return !comparison.absorbedTileOptions[0]?.isSelected;
});

const selectedCount = computed(function () {
    return comparison.absorbedTileOptions.filter((option) => option.isSelected)
        .length;
});

function onCheckboxChange(tileId: string | undefined, isSelected: boolean) {
    if (tileId) {
        emit("update:selection", tileId, isSelected);
    }
}

function onSingleValueChoice(useAbsorbedValue: boolean) {
    onCheckboxChange(singleValueTileId.value, useAbsorbedValue);
}
</script>

<template>
    <section class="merge-section">
        <header class="merge-section-header">
            <h3>{{ sectionTitle }}</h3>
            <Tag
                v-if="selectedCount"
                severity="info"
                :value="
                    $gettext('%{count} selected', {
                        count: String(selectedCount),
                    })
                "
            />
        </header>

        <div class="merge-columns">
            <div class="merge-column">
                <span class="merge-column-heading">
                    {{ $gettext("Kept on this concept") }}
                </span>
                <p
                    v-if="!comparison.survivorTiles.length"
                    class="merge-empty"
                >
                    {{ $gettext("Nothing recorded") }}
                </p>
                <MergeTileCard
                    v-for="(survivorTile, index) in comparison.survivorTiles"
                    :key="survivorTile.tileid ?? index"
                    :tile="survivorTile"
                    :display-node-aliases="
                        comparison.section.displayNodeAliases
                    "
                    :concept-reference-node-aliases="
                        comparison.section.conceptReferenceNodeAliases ?? []
                    "
                    :concept-labels-by-id="conceptLabelsById"
                >
                    <template #control>
                        <RadioButton
                            v-if="replacesSurvivorValue"
                            :model-value="isSurvivorValueKept"
                            :input-id="`keep-${comparison.section.nodegroupAlias}`"
                            :name="`single-${comparison.section.nodegroupAlias}`"
                            :value="true"
                            @update:model-value="onSingleValueChoice(false)"
                        />
                    </template>
                </MergeTileCard>
            </div>

            <div class="merge-column">
                <span class="merge-column-heading">
                    {{ $gettext("Bring across from the other concept") }}
                </span>
                <p
                    v-if="!comparison.absorbedTileOptions.length"
                    class="merge-empty"
                >
                    {{ $gettext("Nothing recorded") }}
                </p>
                <MergeTileCard
                    v-for="(option, index) in comparison.absorbedTileOptions"
                    :key="option.tile.tileid ?? index"
                    :tile="option.tile"
                    :display-node-aliases="
                        comparison.section.displayNodeAliases
                    "
                    :concept-reference-node-aliases="
                        comparison.section.conceptReferenceNodeAliases ?? []
                    "
                    :concept-labels-by-id="conceptLabelsById"
                    :already-on-survivor="option.alreadyOnSurvivor"
                >
                    <template #control>
                        <RadioButton
                            v-if="replacesSurvivorValue"
                            :model-value="!isSurvivorValueKept"
                            :input-id="`take-${comparison.section.nodegroupAlias}`"
                            :name="`single-${comparison.section.nodegroupAlias}`"
                            :value="true"
                            @update:model-value="onSingleValueChoice(true)"
                        />
                        <Checkbox
                            v-else
                            :model-value="option.isSelected"
                            :input-id="`tile-${option.tile.tileid}`"
                            :binary="true"
                            @update:model-value="
                                onCheckboxChange(
                                    option.tile.tileid,
                                    $event as boolean,
                                )
                            "
                        />
                    </template>
                </MergeTileCard>
            </div>
        </div>
    </section>
</template>

<style scoped>
.merge-section {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding-bottom: 1rem;
    border-bottom: 0.0625rem solid var(--p-content-border-color);
}

.merge-section-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.merge-section-header h3 {
    margin: 0;
    font-size: var(--p-lingo-font-size-normal);
    font-weight: var(--p-lingo-font-weight-bold);
}

.merge-columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    align-items: start;
}

.merge-column {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
    min-width: 0;
}

.merge-column-heading {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
}

.merge-empty {
    margin: 0;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
    font-style: italic;
}

@media (max-width: 48rem) {
    .merge-columns {
        grid-template-columns: 1fr;
    }
}
</style>
