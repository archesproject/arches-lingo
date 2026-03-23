<script setup lang="ts">
import { computed, inject } from "vue";

import TreeRowLabel from "@/arches_lingo/components/tree/components/TreeRow/components/TreeRowLabel.vue";
import FocusIcon from "@/arches_lingo/components/tree/components/TreeRow/components/FocusIcon.vue";
import AddChildIcon from "@/arches_lingo/components/tree/components/TreeRow/components/AddChildIcon.vue";
import DeleteIcon from "@/arches_lingo/components/tree/components/TreeRow/components/DeleteIcon.vue";
import ExportIcon from "@/arches_lingo/components/tree/components/TreeRow/components/ExportIcon.vue";

import { NEW } from "@/arches_lingo/constants.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

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

const userStore = useUserStore();

const resourceInstanceLifecycleStateCanEditById = inject(
    "resourceInstanceLifecycleStateCanEditById",
) as Ref<Record<string, boolean>>;

const resourceInstanceLifecycleStateIsRetiredById = inject(
    "resourceInstanceLifecycleStateIsRetiredById",
) as Ref<Record<string, boolean>>;

const isRetired = computed(function () {
    return (
        resourceInstanceLifecycleStateIsRetiredById?.value?.[
            node.data.resource_instance_lifecycle_state_id
        ] === true
    );
});

const shouldShowAddChildButton = computed(function () {
    return (
        node.data.id !== NEW &&
        userStore.isEditor &&
        resourceInstanceLifecycleStateCanEditById?.value?.[
            node.data.resource_instance_lifecycle_state_id
        ] === true
    );
});
</script>

<template>
    <div
        class="tree-row"
        :class="{ retired: isRetired }"
    >
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
            v-if="userStore.isEditor && node.data.id === NEW"
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

.tree-row.retired {
    opacity: 0.5;
    text-decoration: line-through;
}
</style>
