<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

import Button from "primevue/button";

import type { TreeNode } from "primevue/treenode";

const { node, focusLabel, unfocusLabel } = defineProps<{
    node: TreeNode;
    focusLabel: string;
    unfocusLabel: string;
}>();

const route = useRoute();

const focusedNode = defineModel<TreeNode | null>("focusedNode");

const isFocused = computed(() => {
    return focusedNode.value?.data?.id === node.data.id;
});

function toggleFocus() {
    if (isFocused.value) {
        focusedNode.value = null;
    } else {
        focusedNode.value = node;
    }
}
</script>

<template>
    <Button
        v-tooltip="{
            value: isFocused ? unfocusLabel : focusLabel,
            pt: {
                text: {
                    style: { fontFamily: 'sans-serif' },
                },
            },
        }"
        :disabled="route.params.id === 'new' && node.data.id !== 'new'"
        :icon="isFocused ? 'fa fa-search-minus' : 'fa fa-bullseye'"
        role="button"
        size="small"
        style="
            color: var(--p-tree-node-selected-color);
            width: 1rem;
            height: 1rem;
        "
        tabindex="0"
        variant="text"
        :aria-label="isFocused ? unfocusLabel : focusLabel"
        :rounded="true"
        @click.stop="toggleFocus"
        @keyup.enter.stop="toggleFocus"
    />
</template>
