<script setup lang="ts">
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import FacetGroup from "@/arches_lingo/components/advanced-search/FacetGroup.vue";

import type {
    AdvancedSearchOptions,
    ConceptSetItem,
    SearchGroup,
} from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();

const props = defineProps<{
    queryGroup: SearchGroup;
    options: AdvancedSearchOptions;
    conceptSets: ConceptSetItem[];
    isSearching: boolean;
}>();

const emit = defineEmits<{
    (e: "update:queryGroup", group: SearchGroup): void;
    (e: "search"): void;
    (e: "clear"): void;
}>();
</script>

<template>
    <div class="query-panel">
        <FacetGroup
            :group="props.queryGroup"
            :options="props.options"
            :concept-sets="props.conceptSets"
            :depth="0"
            @update:group="emit('update:queryGroup', $event)"
        />

        <div class="search-actions">
            <Button
                :label="$gettext('Search')"
                icon="pi pi-search"
                :loading="props.isSearching"
                @click="emit('search')"
            />
            <Button
                :label="$gettext('Clear')"
                icon="pi pi-eraser"
                severity="secondary"
                outlined
                @click="emit('clear')"
            />
        </div>
    </div>
</template>

<style scoped>
.query-panel {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    flex-shrink: 0;
}

.search-actions {
    display: flex;
    gap: 0.375rem;
    padding-top: 0.75rem;
    border-top: 0.0625rem solid var(--p-highlight-focus-background);
}

.search-actions :deep(.p-button) {
    font-size: var(--p-lingo-font-size-small);
    font-weight: var(--p-lingo-font-weight-normal);
    border-radius: 0.125rem;
}
</style>
