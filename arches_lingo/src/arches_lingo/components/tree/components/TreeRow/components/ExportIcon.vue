<script setup lang="ts">
import Button from "primevue/button";

import { NEW } from "@/arches_lingo/constants.ts";

import type { TreeNode } from "primevue/treenode";

const { node, exportLabel } = defineProps<{
    node: TreeNode;
    exportLabel: string;
}>();

function onExportItem() {}
</script>

<template>
    <Button
        v-tooltip="{
            value: exportLabel,
            pt: {
                text: {
                    style: { fontFamily: 'sans-serif' },
                },
            },
        }"
        :disabled="node.data.id === NEW"
        icon="pi pi-download"
        role="button"
        size="small"
        style="
            color: var(--p-tree-node-selected-color);
            width: 1rem;
            height: 1rem;
        "
        tabindex="1"
        variant="text"
        :aria-label="exportLabel"
        :rounded="true"
        @click.stop="onExportItem"
        @keyup.enter.stop="onExportItem"
    />
</template>
