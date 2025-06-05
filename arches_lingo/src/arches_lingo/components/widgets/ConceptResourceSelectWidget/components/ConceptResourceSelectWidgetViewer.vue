<script setup lang="ts">
import { getItemLabel } from "@/arches_component_lab/utils.ts";
import { getParentLabels } from "@/arches_lingo/utils.ts";
import { ENGLISH } from "@/arches_lingo/constants.ts";
import type { SearchResultItem } from "@/arches_lingo/types.ts";
import { generateArchesURL } from "@/arches/utils/generate-arches-url.ts";

const props = defineProps<{
    value?: SearchResultItem[];
}>();
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
                    getItemLabel(searchResult, ENGLISH.code, ENGLISH.code).value
                }}
            </a>
        </span>
        <span class="concept-hierarchy">
            [
            {{ getParentLabels(searchResult, ENGLISH.code, ENGLISH.code) }}
            ]
        </span>
    </div>
</template>
<style scoped>
.concept-hierarchy {
    font-size: small;
    color: steelblue;
}
</style>
