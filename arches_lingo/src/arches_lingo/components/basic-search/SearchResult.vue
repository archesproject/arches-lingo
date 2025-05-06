<script setup lang="ts">
import { getItemLabel } from "@/arches_component_lab/utils.ts";
import { ENGLISH } from "@/arches_lingo/constants.ts";

import type { PropType } from "vue";
import type { SearchResultItem } from "@/arches_lingo/types.ts";

defineProps({
    searchResult: {
        type: Object as PropType<{ index: number; option: SearchResultItem }>,
        required: true,
    },
});

const getParentLabels = (
    item: SearchResultItem,
    preferredLanguageCode: string,
    systemLanguageCode: string,
): string => {
    const arrowIcon = " → ";

    return item.parents[0].reduce((acc, parent, index) => {
        const label = getItemLabel(
            parent,
            preferredLanguageCode,
            systemLanguageCode,
        ).value;
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
        <i
            class="pi pi-paperclip"
            aria-hidden="true"
        />

        <div style="margin: 0 0.5rem">
            {{
                getItemLabel(searchResult.option, ENGLISH.code, ENGLISH.code)
                    .value
            }}
        </div>

        <div class="search-result-hierarchy">
            [
            {{
                getParentLabels(searchResult.option, ENGLISH.code, ENGLISH.code)
            }}
            ]
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
