<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import {
    DRAFT_LIFECYCLE_STATE_ID,
    RETIRED_LIFECYCLE_STATE_ID,
} from "@/arches_lingo/constants.ts";
import { dataIsScheme } from "@/arches_lingo/utils.ts";
import LifecycleStateBadge from "@/arches_lingo/components/generic/LifecycleStateBadge.vue";
import type { Concept, Scheme } from "@/arches_lingo/types.ts";
import type { TreeNode } from "primevue/treenode";

const { node, filterValue } = defineProps<{
    node: TreeNode;
    filterValue: string;
}>();

const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

function tokenizeLabel(
    label: string,
    filter?: string,
): { text: string; highlight: boolean }[] {
    if (!filter) {
        return [{ text: label, highlight: false }];
    }

    const regex = new RegExp(`(${filter})`, "gi");
    const parts = label.split(regex);

    return parts.reduce<{ text: string; highlight: boolean }[]>((acc, part) => {
        if (part) {
            acc.push({
                text: part,
                highlight: part.toLowerCase() === filter.toLowerCase(),
            });
        }
        return acc;
    }, []);
}

const tokenizedLabel = computed(() => {
    if (!node.data) {
        return [];
    }

    const unstyledLabel = getItemLabel(
        node.data,
        selectedLanguage.value.code,
        systemLanguage.value.code,
    ).value;

    return tokenizeLabel(unstyledLabel, filterValue);
});

const nodeData = computed(() => node.data as Concept | Scheme);

const lifecycleStateId = computed(
    () => nodeData.value?.resource_instance_lifecycle_state_id,
);

const lifecycleStateName = computed(
    () => nodeData.value?.resource_instance_lifecycle_state_name,
);

const shouldShowLifecycleBadge = computed(() => {
    if (!lifecycleStateId.value || !lifecycleStateName.value) return false;
    if (dataIsScheme(nodeData.value)) return true;
    return (
        lifecycleStateId.value === DRAFT_LIFECYCLE_STATE_ID ||
        lifecycleStateId.value === RETIRED_LIFECYCLE_STATE_ID
    );
});
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
