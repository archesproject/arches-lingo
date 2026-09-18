<script setup lang="ts">
import { computed } from "vue";

import { useGettext } from "vue3-gettext";
import { storeToRefs } from "pinia";
import Tag from "primevue/tag";

import {
    getDisplayValue,
    getReferencedResourceIds,
} from "@/arches_lingo/components/concept/ConceptMerge/utils.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

import type { Label } from "@/arches_controlled_lists/types.ts";
import type { MergeTile } from "@/arches_lingo/components/concept/ConceptMerge/types.ts";

const {
    tile,
    displayNodeAliases,
    conceptReferenceNodeAliases,
    conceptLabelsById,
    alreadyOnSurvivor,
} = defineProps<{
    tile: MergeTile;
    displayNodeAliases: string[];
    conceptReferenceNodeAliases: string[];
    conceptLabelsById: Map<string, Label[]>;
    alreadyOnSurvivor?: boolean;
}>();

const { $gettext } = useGettext();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

// A referenced concept is named the way it is everywhere else in Lingo. Until its
// labels arrive the tile's own display value stands in, so the card is never blank.
function resolveNodeText(nodeAlias: string) {
    if (!conceptReferenceNodeAliases.includes(nodeAlias)) {
        return getDisplayValue(tile, nodeAlias);
    }

    const referencedNames = getReferencedResourceIds(tile, nodeAlias)
        .map((conceptId) => {
            const labels = conceptLabelsById.get(conceptId);
            if (!labels?.length) {
                return "";
            }
            return getItemLabel(
                { labels },
                selectedLanguage.value.code,
                systemLanguage.value.code,
            ).value;
        })
        .filter(Boolean);

    return referencedNames.length
        ? referencedNames.join(", ")
        : getDisplayValue(tile, nodeAlias);
}

const displayValues = computed(function () {
    return displayNodeAliases
        .map(resolveNodeText)
        .filter((displayValue) => displayValue !== "");
});

const primaryValue = computed(function () {
    return displayValues.value[0] ?? $gettext("(empty)");
});

const secondaryValues = computed(function () {
    return displayValues.value.slice(1);
});
</script>

<template>
    <div
        class="merge-tile-card"
        :class="{ muted: alreadyOnSurvivor }"
    >
        <div class="merge-tile-control">
            <slot name="control" />
        </div>
        <div class="merge-tile-body">
            <span class="merge-tile-primary">{{ primaryValue }}</span>
            <span
                v-if="secondaryValues.length"
                class="merge-tile-secondary"
            >
                {{ secondaryValues.join(" · ") }}
            </span>
            <Tag
                v-if="alreadyOnSurvivor"
                class="merge-tile-tag"
                severity="secondary"
                :value="$gettext('Already present')"
            />
        </div>
    </div>
</template>

<style scoped>
.merge-tile-card {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.5rem 0.625rem;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.25rem;
    background: var(--p-content-background);
}

.merge-tile-card.muted {
    opacity: 0.6;
}

.merge-tile-control {
    display: flex;
    align-items: center;
    min-height: 1.5rem;
}

.merge-tile-body {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    min-width: 0;
}

.merge-tile-primary {
    font-size: var(--p-lingo-font-size-normal);
    color: var(--p-text-color);
    overflow-wrap: anywhere;
}

.merge-tile-secondary {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
    overflow-wrap: anywhere;
}

.merge-tile-tag {
    align-self: flex-start;
    margin-top: 0.25rem;
    font-size: var(--p-lingo-font-size-xxsmall);
}
</style>
