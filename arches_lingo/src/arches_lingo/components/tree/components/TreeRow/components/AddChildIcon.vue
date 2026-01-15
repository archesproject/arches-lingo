<script setup lang="ts">
import { useRouter } from "vue-router";

import Button from "primevue/button";

import { NEW_CONCEPT } from "@/arches_lingo/constants.ts";
import { navigateToSchemeOrConcept } from "@/arches_lingo/utils.ts";
import { NEW } from "@/arches_lingo/constants.ts";

import type { TreeNode } from "primevue/treenode";

const { node, addChildLabel } = defineProps<{
    node: TreeNode;
    addChildLabel?: string;
}>();

const router = useRouter();

function onAddChild() {
    navigateToSchemeOrConcept(router, NEW_CONCEPT, {
        scheme: node.data.schemeId,
        parent: node.data.id,
        parentTreeKey: node.key,
    });
}
</script>

<template>
    <Button
        v-tooltip="{
            value: addChildLabel,
            pt: {
                text: {
                    style: { fontFamily: 'sans-serif' },
                },
            },
        }"
        :disabled="node.data.id === NEW"
        icon="pi pi-plus"
        role="button"
        size="small"
        style="
            color: var(--p-tree-node-selected-color);
            width: 1rem;
            height: 1rem;
        "
        tabindex="1"
        variant="text"
        :aria-label="addChildLabel"
        :rounded="true"
        @click.stop="onAddChild"
        @keyup.enter.stop="onAddChild"
    />
</template>
