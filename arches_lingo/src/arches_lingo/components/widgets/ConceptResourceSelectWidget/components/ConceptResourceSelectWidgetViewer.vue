<script setup lang="ts">
import { storeToRefs } from "pinia";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { getParentLabels } from "@/arches_lingo/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import type { SearchResultItem } from "@/arches_lingo/types.ts";

const props = defineProps<{
    value?: SearchResultItem[];
}>();

const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());
</script>
<template>
    <div
        v-for="searchResult in props.value"
        :key="searchResult.id"
    >
        <span>
            <RouterLink
                :to="{
                    name: routeNames.concept,
                    params: {
                        id: searchResult.id,
                    },
                }"
                class="text-link"
            >
                {{
                    getItemLabel(
                        searchResult,
                        selectedLanguage.code,
                        systemLanguage.code,
                    ).value
                }}
            </RouterLink>
        </span>
        <span class="concept-hierarchy">
            [{{
                getParentLabels(
                    searchResult,
                    selectedLanguage.code,
                    systemLanguage.code,
                )
            }}]
        </span>
    </div>
</template>
<style scoped>
.concept-hierarchy {
    font-size: small;
    color: var(--p-primary-500);
}
</style>
