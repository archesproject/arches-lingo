<script setup lang="ts">
import { computed, inject } from "vue";

import TreeRowLabel from "@/arches_lingo/components/tree/components/TreeRow/components/TreeRowLabel.vue";
import FocusIcon from "@/arches_lingo/components/tree/components/TreeRow/components/FocusIcon.vue";
import AddChildIcon from "@/arches_lingo/components/tree/components/TreeRow/components/AddChildIcon.vue";
import DeleteIcon from "@/arches_lingo/components/tree/components/TreeRow/components/DeleteIcon.vue";
import ExportIcon from "@/arches_lingo/components/tree/components/TreeRow/components/ExportIcon.vue";

import { NEW } from "@/arches_lingo/constants.ts";

import type { Ref } from "vue";
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

const resourceInstanceLifecycleStateCanEditById = inject(
    "resourceInstanceLifecycleStateCanEditById",
) as Ref<Record<string, boolean>>;

const shouldShowAddChildButton = computed(() => {
    if (node.data.id === NEW) {
        return false;
    }

    const nodeDataObject = node.data as unknown as Record<string, unknown>;
    const lifecycleStateIdValue =
        nodeDataObject.resource_instance_lifecycle_state_id;

    if (typeof lifecycleStateIdValue !== "string") {
        return false;
    }

    return Boolean(
        resourceInstanceLifecycleStateCanEditById?.value?.[
            lifecycleStateIdValue
        ],
    );
});
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
            v-if="shouldShowAddChildButton"
            :node="node"
            :add-child-label="addChildLabel"
        />
        <DeleteIcon
            v-if="node.data.id === NEW"
            :delete-label="deleteLabel"
        />
        <ExportIcon
            v-if="node.data.id !== NEW"
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
