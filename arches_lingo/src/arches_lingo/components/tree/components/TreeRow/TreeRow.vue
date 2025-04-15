<script setup lang="ts">
import TreeRowLabel from "@/arches_lingo/components/tree/components/TreeRow/components/TreeRowLabel.vue";
import FocusIcon from "@/arches_lingo/components/tree/components/TreeRow/components/FocusIcon.vue";
import AddChildIcon from "@/arches_lingo/components/tree/components/TreeRow/components/AddChildIcon.vue";

import type { TreeNode } from "primevue/treenode";

const { node, focusLabel, unfocusLabel, filterValue } = defineProps<{
    node: TreeNode;
    focusLabel: string;
    unfocusLabel: string;
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
            :add-child-label="'Add Child'"
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
