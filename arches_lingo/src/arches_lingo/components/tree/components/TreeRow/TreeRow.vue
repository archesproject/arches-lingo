<script setup lang="ts">
import TreeRowLabel from "@/arches_lingo/components/tree/components/TreeRow/components/TreeRowLabel.vue";
import FocusIcon from "@/arches_lingo/components/tree/components/TreeRow/components/FocusIcon.vue";
import AddChildIcon from "@/arches_lingo/components/tree/components/TreeRow/components/AddChildIcon.vue";
import DeleteIcon from "@/arches_lingo/components/tree/components/TreeRow/components/DeleteIcon.vue";
import ExportIcon from "@/arches_lingo/components/tree/components/TreeRow/components/ExportIcon.vue";

import type { TreeNode } from "primevue/treenode";

const { node, focusLabel, unfocusLabel, addChildLabel, filterValue } =
    defineProps<{
        node: TreeNode;
        focusLabel: string;
        unfocusLabel: string;
        addChildLabel: string;
        deleteLabel: string;
        exportLabel: string;
        filterValue: string;
    }>();

const focusedNode = defineModel<TreeNode | null>("focusedNode");
</script>

<template>
    <div class="tree-row">
        <TreeRowLabel
            :filter-value="filterValue"
            :node="node"
        />
        <FocusIcon
            v-model:focused-node="focusedNode"
            :focus-label="focusLabel"
            :node="node"
            :unfocus-label="unfocusLabel"
        />
        <AddChildIcon
            :node="node"
            :add-child-label="addChildLabel"
        />
        <DeleteIcon
            :node="node"
            :delete-label="deleteLabel"
        />
        <ExportIcon
            :node="node"
            :export-label="exportLabel"
        />
    </div>
</template>

<style scoped>
.tree-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0 0.5rem;
}
</style>
