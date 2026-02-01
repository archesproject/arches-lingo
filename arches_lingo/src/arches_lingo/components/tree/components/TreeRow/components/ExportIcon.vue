<script setup lang="ts">
import { ref } from "vue";

import Button from "primevue/button";

import ExportThesauri from "@/arches_lingo/components/scheme/SchemeHeader/components/ExportThesauri.vue";
import { NEW } from "@/arches_lingo/constants.ts";

import type { TreeNode } from "primevue/treenode";

const { node, exportLabel } = defineProps<{
    node: TreeNode;
    exportLabel: string;
}>();

const showExportDialog = ref(false);
const exportDialogKey = ref(0);

function openExportDialog() {
    exportDialogKey.value++;
    showExportDialog.value = true;
}
</script>

<template>
    <Button
        v-tooltip="{
            value: exportLabel,
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
        @click.stop="openExportDialog"
        @keyup.enter.stop="openExportDialog"
    />
    <ExportThesauri
        v-if="showExportDialog"
        :key="exportDialogKey"
        :resource-id="node.key"
        :resource-name="node.label"
    />
</template>

