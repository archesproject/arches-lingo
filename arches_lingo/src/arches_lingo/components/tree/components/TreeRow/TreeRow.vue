<script setup lang="ts">
import TreeRowLabel from "@/arches_lingo/components/tree/components/TreeRow/components/TreeRowLabel.vue"
import FocusIcon from "@/arches_lingo/components/tree/components/TreeRow/components/FocusIcon.vue"
import AddChildIcon from "@/arches_lingo/components/tree/components/TreeRow/components/AddChildIcon.vue"

import type { TreeNode } from "primevue/treenode"

const { node, focusLabel, unfocusLabel, filterValue } = defineProps<{
    node: TreeNode,
    focusLabel: string,
    unfocusLabel: string,
    filterValue: string,
}>();

const focusedNode = defineModel<TreeNode | null>("focusedNode");

console.log(node)
</script>

<template>
    <div style="display: flex; align-items: center; gap: 0.5rem; margin: 0 0.5rem;">
        <TreeRowLabel 
            :filter-value="filterValue" 
            :node="node" 
        />
        <FocusIcon 
            v-model:focused-node="focusedNode" 
            :focusLabel="focusLabel" 
            :node="node" 
            :unfocusLabel="unfocusLabel"
        />
        <AddChildIcon 
            :node="node" 
            :addChildLabel="'Add Child'"
        />
    </div>
</template>
