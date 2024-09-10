<script setup lang="ts">
import type { Concept } from "@/arches_lingo/types.ts";
import { getItemLabel } from "@/arches_lingo/utils.ts";

defineProps({
    searchResult: {
        type: Object,
        required: true,
    },
});

const getParentLabels = (item: Concept, preferredLanguage: string): string => {
    const arrowIcon = " → ";

    return item.parents.reduce((acc, parent, index) => {
        const label = getItemLabel(parent as Concept, preferredLanguage);
        if (label) {
            return acc + (index > 0 ? arrowIcon : "") + label;
        }
        return acc;
    }, "");
};
</script>

<template>
    <div
        class="search-result"
        :class="{ 'is-even': searchResult.index % 2 === 0 }"
    >
        <i class="pi pi-paperclip" />

        <div style="margin: 0 0.5rem">
            {{ getItemLabel(searchResult.option, "en-US") }}
        </div>

        <div class="search-result-hierarchy">
            [ {{ getParentLabels(searchResult.option, "en-US") }} ]
        </div>
    </div>
</template>

<style scoped>
.search-result {
    height: 100%;
    width: 100%;
    padding: 0.5rem;
    display: flex;
    align-items: center;
    background-color: white;
    border-bottom: 1px solid #ddd;
    font-family: sans-serif;
}

.search-result-hierarchy {
    margin: 0 0.5rem;
    font-size: small;
    color: steelblue;
}

.p-focus > .search-result {
    background-color: #9cc3e4;
}

.is-even {
    background-color: #d3e5f4;
}
</style>
