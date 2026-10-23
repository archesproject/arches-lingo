<script setup lang="ts">
import { computed } from "vue";

import { useGettext } from "vue3-gettext";
import Checkbox from "primevue/checkbox";
import RadioButton from "primevue/radiobutton";
import Tag from "primevue/tag";

import MergeDigitalObjectCard from "@/arches_lingo/components/concept/ConceptMerge/components/MergeDigitalObjectCard.vue";
import MergeTileCard from "@/arches_lingo/components/concept/ConceptMerge/components/MergeTileCard.vue";

import { countSelectedValues } from "@/arches_lingo/components/concept/ConceptMerge/utils.ts";

import type { Label } from "@/arches_controlled_lists/types.ts";
import type { DigitalObjectInstance } from "@/arches_lingo/types.ts";
import type { SectionComparison } from "@/arches_lingo/components/concept/ConceptMerge/types.ts";

const { sectionTitle, comparison, survivorLabel, absorbedLabel } = defineProps<{
    sectionTitle: string;
    comparison: SectionComparison;
    survivorLabel: string | undefined;
    absorbedLabel: string | undefined;
    conceptLabelsById: Map<string, Label[]>;
    digitalObjectsById: Map<string, DigitalObjectInstance>;
}>();

const emit = defineEmits<{
    (event: "update:selection", tileId: string, isSelected: boolean): void;
    (
        event: "update:digitalObjectSelection",
        digitalObjectId: string,
        isSelected: boolean,
    ): void;
}>();

const { $gettext } = useGettext();

const singleValueOption = computed(function () {
    return comparison.absorbedTileOptions[0];
});

// A single value replaces rather than appends, so it is a choice between the two
// sides -- unless both already hold the same value, when there is nothing to choose.
const replacesSurvivorValue = computed(function () {
    return (
        comparison.section.cardinality === "1" &&
        comparison.survivorTiles.length > 0 &&
        !singleValueOption.value?.alreadyOnSurvivor
    );
});

const isSurvivorValueKept = computed(function () {
    return !singleValueOption.value?.isSelected;
});

const selectedCount = computed(function () {
    return countSelectedValues(comparison);
});

const survivorColumnHeading = computed(function () {
    return $gettext('Already on "%{name}"', { name: survivorLabel ?? "" });
});

const absorbedColumnHeading = computed(function () {
    return $gettext('Bring across from "%{name}"', {
        name: absorbedLabel ?? "",
    });
});

const isSurvivorColumnEmpty = computed(function () {
    return (
        !comparison.survivorTiles.length &&
        !comparison.survivorDigitalObjectIds.length
    );
});

const isAbsorbedColumnEmpty = computed(function () {
    return (
        !comparison.absorbedTileOptions.length &&
        !comparison.absorbedDigitalObjectOptions.length
    );
});

function onCheckboxChange(tileId: string | undefined, isSelected: boolean) {
    if (tileId) {
        emit("update:selection", tileId, isSelected);
    }
}

function onSingleValueChoice(useAbsorbedValue: boolean) {
    onCheckboxChange(singleValueOption.value?.tile.tileid, useAbsorbedValue);
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
            v-if="comparison.isBlocked"
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
                    {{ survivorColumnHeading }}
                </span>
                <p
                    v-if="isSurvivorColumnEmpty"
                    class="merge-empty"
                >
                    {{ $gettext("Nothing recorded") }}
                </p>
                <MergeDigitalObjectCard
                    v-for="digitalObjectId in comparison.survivorDigitalObjectIds"
                    :key="digitalObjectId"
                    :digital-object="digitalObjectsById.get(digitalObjectId)"
                />
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
                            :disabled="comparison.isBlocked"
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
                    {{ absorbedColumnHeading }}
                </span>
                <p
                    v-if="isAbsorbedColumnEmpty"
                    class="merge-empty"
                >
                    {{ $gettext("Nothing recorded") }}
                </p>
                <MergeDigitalObjectCard
                    v-for="option in comparison.absorbedDigitalObjectOptions"
                    :key="option.digitalObjectId"
                    :digital-object="
                        digitalObjectsById.get(option.digitalObjectId)
                    "
                    :already-on-survivor="option.alreadyOnSurvivor"
                >
                    <template #control>
                        <Checkbox
                            :model-value="option.isSelected"
                            :disabled="
                                comparison.isBlocked || option.alreadyOnSurvivor
                            "
                            :input-id="`digital-object-${option.digitalObjectId}`"
                            :binary="true"
                            @update:model-value="
                                emit(
                                    'update:digitalObjectSelection',
                                    option.digitalObjectId,
                                    $event as boolean,
                                )
                            "
                        />
                    </template>
                </MergeDigitalObjectCard>
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
                            :disabled="comparison.isBlocked"
                            :input-id="`take-${comparison.section.nodegroupAlias}`"
                            :name="`single-${comparison.section.nodegroupAlias}`"
                            :value="true"
                            @update:model-value="onSingleValueChoice(true)"
                        />
                        <Checkbox
                            v-else
                            :model-value="option.isSelected"
                            :disabled="
                                comparison.isBlocked || option.alreadyOnSurvivor
                            "
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

.merge-column-heading {
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-400);
}

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
