<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

import Button from "primevue/button";

import type { TreeNode } from "primevue/treenode";

import { NEW } from "@/arches_lingo/constants.ts";

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
                    style: {
                        style: { fontFamily: 'sans-serif' },
                        fontSize: '0.875rem',
                        paddingBottom: '0.75rem',
                        marginLeft: '0.5rem',
                        paddingInlineStart: '0.65rem',
                    },
                },
            },
        }"
        :disabled="route.params.id === NEW && node.data.id !== NEW"
        :icon="isFocused ? 'pi pi-search-minus' : 'pi pi-bullseye'"
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
