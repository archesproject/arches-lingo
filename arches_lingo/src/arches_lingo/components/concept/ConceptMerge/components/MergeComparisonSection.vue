<script setup lang="ts">
import { computed } from "vue";

import { useGettext } from "vue3-gettext";
import Checkbox from "primevue/checkbox";
import RadioButton from "primevue/radiobutton";
import Tag from "primevue/tag";

import MergeTileCard from "@/arches_lingo/components/concept/ConceptMerge/components/MergeTileCard.vue";

import type { Label } from "@/arches_controlled_lists/types.ts";
import type { SectionComparison } from "@/arches_lingo/components/concept/ConceptMerge/types.ts";

const { sectionTitle, comparison, isBlocked } = defineProps<{
    sectionTitle: string;
    comparison: SectionComparison;
    conceptLabelsById: Map<string, Label[]>;
    // A scheme-scoped section in a merge across schemes. Shown rather than
    // hidden, so the editor can see what is being left behind, but nothing in
    // it can be chosen.
    isBlocked: boolean;
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
            <div class="merge-section-title">
                <h3>{{ sectionTitle }}</h3>
                <Tag
                    v-if="selectedCount"
                    severity="secondary"
                    :value="
                        $gettext('%{count} selected', {
                            count: String(selectedCount),
                        })
                    "
                />
            </div>
        </header>

        <p
            v-if="isBlocked"
            class="merge-section-blocked"
        >
            {{
                $gettext(
                    "These values belong to the other concept's scheme and cannot be brought across. They stay with that concept.",
                )
            }}
        </p>

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
                            :disabled="isBlocked"
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
                            :disabled="isBlocked"
                            :input-id="`take-${comparison.section.nodegroupAlias}`"
                            :name="`single-${comparison.section.nodegroupAlias}`"
                            :value="true"
                            @update:model-value="onSingleValueChoice(true)"
                        />
                        <Checkbox
                            v-else
                            :model-value="option.isSelected"
                            :disabled="isBlocked"
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
}

/* Matches the section headers the concept report uses, so a section reads the
   same here as it does behind the dialog. See ComponentManager's .section-header. */
.merge-section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
    padding-bottom: 0.5rem;
}

.merge-section-blocked {
    margin: 0;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
}

.merge-section-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.merge-section-header h3 {
    margin: 0;
    font-size: var(--p-lingo-font-size-medium);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-500);
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

/* These name the two sides the way a table names its columns, so they take the
   column-title treatment rather than reading as body copy. */
.merge-column-heading {
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-400);
}

/* Lingo renders "nothing here yet" copy light and unemphasised rather than
   italic; see MetaStringViewer's .no-data. */
.merge-empty {
    margin: 0;
    padding: 0.5rem 0;
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-light);
    color: var(--p-inputtext-placeholder-color);
}

@media (max-width: 48rem) {
    .merge-columns {
        grid-template-columns: 1fr;
    }
}
</style>
