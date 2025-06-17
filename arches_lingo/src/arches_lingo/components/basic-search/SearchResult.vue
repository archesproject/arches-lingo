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
        <div style="margin: 0 0.5rem">
            <span>
                <i
                    class="pi pi-paperclip concept-icon"
                    aria-hidden="true"
                />
                {{
                    getItemLabel(
                        searchResult.option,
                        ENGLISH.code,
                        ENGLISH.code,
                    ).value
                }}
            </span>
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
    align-items: flex-start;
    flex-direction: column;
    background-color: var(--p-dialog-background);
    border-bottom: 0.06rem solid var(--p-search-result-border-bottom);
    color: var(--p-search-result-color);
}

.search-result-hierarchy {
    margin: 0 0.5rem;
    font-size: var(--p-lingo-font-size-xsmall);
    color: var(--p-search-result-hierarchy-color);
}

.p-focus > .search-result {
    background-color: var(--p-search-result-focus-background);
}

.is-even {
    background-color: var(--p-search-result-is-even-background);
}

.concept-icon {
    font-size: var(--p-lingo-font-size-xxsmall);
}
</style>
