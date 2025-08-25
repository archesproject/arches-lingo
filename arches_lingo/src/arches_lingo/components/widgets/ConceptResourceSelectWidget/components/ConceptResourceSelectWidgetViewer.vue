<script setup lang="ts">
import { inject } from "vue";
import { getItemLabel } from "@/arches_lingo/utils.ts";
import { getParentLabels } from "@/arches_lingo/utils.ts";
import {
    selectedLanguageKey,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";
import type { SearchResultItem } from "@/arches_lingo/types.ts";
import { generateArchesURL } from "@/arches/utils/generate-arches-url.ts";
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
            <a
                :href="
                    generateArchesURL('resource_editor', {
                        resourceid: searchResult.id,
                    })
                "
            >
                {{
                    getItemLabel(
                        searchResult,
                        selectedLanguage.code,
                        systemLanguage.code,
                    ).value
                }}
            </a>
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
