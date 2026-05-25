<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { getParentLabels } from "@/arches_lingo/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import type { ResourceInstanceListOption } from "@/arches_component_lab/datatypes/resource-instance-list/types.ts";
import type { SearchResultItem } from "@/arches_lingo/types.ts";

interface DisplayItem {
    id: string;
    label: string;
    parentsLabel: string | null;
}

const props = defineProps<{
    value?: SearchResultItem[] | ResourceInstanceListOption[] | null;
}>();

const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

const displayItems = computed<DisplayItem[]>(() => {
    if (!props.value?.length) {
        return [];
    }

    const firstItem = props.value[0];
    if ("resource_id" in firstItem) {
        return (props.value as ResourceInstanceListOption[]).map((item) => ({
            id: item.resource_id,
            label: item.display_value,
            parentsLabel: null,
        }));
    }

    return (props.value as SearchResultItem[]).map((item) => ({
        id: item.id,
        label: getItemLabel(
            item,
            selectedLanguage.value.code,
            systemLanguage.value.code,
        ).value,
        parentsLabel: getParentLabels(
            item,
            selectedLanguage.value.code,
            systemLanguage.value.code,
        ),
    }));
});
</script>

<template>
    <div
        v-for="displayItem in displayItems"
        :key="displayItem.id"
    >
        <span>
            <RouterLink
                :to="{
                    name: routeNames.concept,
                    params: {
                        id: displayItem.id,
                    },
                }"
                class="text-link"
            >
                {{ displayItem.label }}
            </RouterLink>
        </span>
        <span
            v-if="displayItem.parentsLabel"
            class="concept-hierarchy"
        >
            [{{ displayItem.parentsLabel }}]
        </span>
    </div>
</template>

<style scoped>
.concept-hierarchy {
    font-size: small;
    color: var(--p-primary-500);
}
</style>
