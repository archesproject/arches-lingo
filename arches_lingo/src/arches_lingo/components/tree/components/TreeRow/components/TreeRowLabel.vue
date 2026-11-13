<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

import LifecycleStateBadge from "@/arches_lingo/components/generic/LifecycleStateBadge.vue";

import {
    getDisplayedLifecycleStateName,
    splitLabelForFilterHighlight,
} from "@/arches_lingo/utils.ts";

import type { TreeNode } from "primevue/treenode";

const { node, filterValue } = defineProps<{
    node: TreeNode;
    filterValue: string;
}>();

const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

const tokenizedLabel = computed(() => {
    if (!node.data) {
        return [];
    }

    const unstyledLabel = getItemLabel(
        node.data,
        selectedLanguage.value.code,
        systemLanguage.value.code,
    ).value;

    return splitLabelForFilterHighlight(unstyledLabel, filterValue);
});

const lifecycleStateId = computed(
    () => node.data?.resource_instance_lifecycle_state_id,
);

const lifecycleStateName = computed(
    () => node.data?.resource_instance_lifecycle_state_name,
);

const shouldShowLifecycleBadge = computed(
    () =>
        !!node.data && getDisplayedLifecycleStateName(node.data) !== undefined,
);
</script>

<template>
    <div class="tree-row-label">
        <div>
            <template
                v-for="(token, index) in tokenizedLabel"
                :key="index"
            >
                <b v-if="token.highlight">{{ token.text }}</b>
                <span v-else>{{ token.text }}</span>
            </template>
        </div>
        <LifecycleStateBadge
            v-if="shouldShowLifecycleBadge"
            :lifecycle-state-id="lifecycleStateId"
            :lifecycle-state-name="lifecycleStateName"
        />
    </div>
</template>

<style scoped>
.tree-row-label {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    min-width: 0;
}
</style>
