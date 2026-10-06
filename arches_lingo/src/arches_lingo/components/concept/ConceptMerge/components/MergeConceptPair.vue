<script setup lang="ts">
import { computed } from "vue";

import { useGettext } from "vue3-gettext";

import SearchResult from "@/arches_lingo/components/basic-search/SearchResult.vue";

import type { SearchResultItem } from "@/arches_lingo/types.ts";

// An odd index keeps SearchResult off its striped background.
const UNSTRIPED_RESULT_INDEX = 1;

const { survivorConcept, survivorLabel, absorbedConcept, isCrossScheme } =
    defineProps<{
        survivorConcept: SearchResultItem | undefined;
        survivorLabel: string | undefined;
        absorbedConcept: SearchResultItem | undefined;
        isCrossScheme: boolean;
    }>();

const { $gettext } = useGettext();

const absorbedRoleText = computed(function () {
    if (isCrossScheme) {
        return $gettext("Copying values from");
    }
    return $gettext("Merging in");
});
</script>

<template>
    <dl class="merge-concept-pair">
        <div class="merge-concept-role">
            <dt>{{ $gettext("Keeping") }}</dt>
            <dd>
                <SearchResult
                    v-if="survivorConcept"
                    :search-result="{
                        index: UNSTRIPED_RESULT_INDEX,
                        option: survivorConcept,
                    }"
                />
                <span
                    v-else
                    class="merge-concept-fallback"
                >
                    {{ survivorLabel }}
                </span>
            </dd>
        </div>
        <div class="merge-concept-role">
            <dt>{{ absorbedRoleText }}</dt>
            <dd>
                <SearchResult
                    v-if="absorbedConcept"
                    :search-result="{
                        index: UNSTRIPED_RESULT_INDEX,
                        option: absorbedConcept,
                    }"
                />
                <span
                    v-else
                    class="merge-concept-fallback is-empty"
                >
                    {{ $gettext("Not chosen yet") }}
                </span>
            </dd>
        </div>
    </dl>
</template>

<style scoped>
.merge-concept-pair {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 0.5rem 0.75rem;
    margin: 0;
}

.merge-concept-role {
    display: contents;
}

.merge-concept-role dt {
    padding-top: 0.5rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
}

.merge-concept-role dd {
    margin: 0;
    min-width: 0;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.125rem;
}

.merge-concept-role dd :deep(.search-result) {
    border-bottom: none;
}

.merge-concept-fallback {
    display: block;
    padding: 0.5rem 1rem;
    font-size: var(--p-lingo-font-size-small);
}

.merge-concept-fallback.is-empty {
    color: var(--p-inputtext-placeholder-color);
}
</style>
