<script setup lang="ts">
import Button from "primevue/button";

import { NEW } from "@/arches_lingo/constants.ts";

import type { TreeNode } from "primevue/treenode";

const { node, deleteLabel } = defineProps<{
    node: TreeNode;
    deleteLabel: string;
}>();

function onDeleteItem() {}
</script>

<template>
    <Button
        v-tooltip="{
            value: deleteLabel,
            pt: {
                text: {
                    style: { fontFamily: 'sans-serif' },
                },
            },
        }"
        :disabled="node.data.id === NEW"
        icon="pi pi-trash"
        role="button"
        size="small"
        style="color: var(--p-tree-node-selected-color)"
        tabindex="1"
        variant="text"
        :aria-label="deleteLabel"
        :rounded="true"
        @click.stop="onDeleteItem"
        @keyup.enter.stop="onDeleteItem"
    />
</template>
