<script setup lang="ts">
import { inject } from "vue";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { getParentLabels } from "@/arches_lingo/utils.ts";
import {
    selectedLanguageKey,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";

import type { PropType } from "vue";
import type { SearchResultItem } from "@/arches_lingo/types.ts";

const selectedLanguage = inject(selectedLanguageKey);
const systemLanguage = inject(systemLanguageKey);

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
                    class="pi pi-paperclip concept-icon"
                    aria-hidden="true"
                />
                {{
                    getItemLabel(
                        searchResult.option,
                        selectedLanguage?.code ?? "en",
                        systemLanguage?.code ?? "en",
                    ).value
                }}
            </span>
        </div>

        <div class="search-result-hierarchy">
            [
            {{
                getParentLabels(
                    searchResult.option,
                    selectedLanguage?.code ?? "en",
                    systemLanguage?.code ?? "en",
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
