<script setup lang="ts">
import { storeToRefs } from "pinia";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { getParentLabels, getConceptIcon } from "@/arches_lingo/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

import type { PropType } from "vue";
import type { SearchResultItem } from "@/arches_lingo/types.ts";

const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

defineProps({
    searchResult: {
        type: Object as PropType<{ index: number; option: SearchResultItem }>,
        required: true,
    },
});
</script>

<template>
    <div
        class="search-result"
        :class="{ 'is-even': searchResult.index % 2 === 0 }"
    >
        <div style="margin: 0 0.5rem">
            <span>
                <i
                    :class="[
                        getConceptIcon(searchResult.option),
                        'concept-icon',
                    ]"
                    aria-hidden="true"
                />
                {{
                    getItemLabel(
                        searchResult.option,
                        selectedLanguage.code,
                        systemLanguage.code,
                    ).value
                }}
            </span>
        </div>

        <div class="search-result-hierarchy">
            [
            {{
                getParentLabels(
                    searchResult.option,
                    selectedLanguage.code,
                    systemLanguage.code,
                )
            }}
            ]
        </div>
    </div>
</template>

<style scoped>
.search-result {
    height: 100%;
    width: 100%;
    font-size: 0.875rem;
    padding: 0.5rem;
    display: flex;
    align-items: flex-start;
    flex-direction: column;
    background-color: var(--p-dialog-background);
    border-bottom: 0.0625rem solid var(--p-search-result-border-bottom);
    color: var(--p-search-result-color);
    gap: 0.125rem;
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
