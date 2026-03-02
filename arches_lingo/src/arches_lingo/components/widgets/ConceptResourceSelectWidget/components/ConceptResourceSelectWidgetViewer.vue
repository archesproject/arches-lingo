<script setup lang="ts">
import { inject } from "vue";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { getParentLabels } from "@/arches_lingo/utils.ts";
import {
    selectedLanguageKey,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import type { SearchResultItem } from "@/arches_lingo/types.ts";
import type { Ref } from "vue";
import type { Language } from "@/arches_component_lab/types";

const props = defineProps<{
    value?: SearchResultItem[];
}>();

const selectedLanguage = inject(selectedLanguageKey) as Ref<Language>;
const systemLanguage = inject(systemLanguageKey) as Language;
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
