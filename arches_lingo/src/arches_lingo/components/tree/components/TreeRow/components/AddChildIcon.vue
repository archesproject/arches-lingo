<script setup lang="ts">
import { useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useConfirm } from "primevue/useconfirm";

import Button from "primevue/button";

import {
    DANGER,
    NEW,
    NEW_CONCEPT,
    SECONDARY,
} from "@/arches_lingo/constants.ts";
import { navigateToSchemeOrConcept } from "@/arches_lingo/utils.ts";
import { useEditorDirtyState } from "@/arches_lingo/composables/useEditorDirtyState.ts";

import type { TreeNode } from "primevue/treenode";

const { node, addChildLabel } = defineProps<{
    node: TreeNode;
    addChildLabel?: string;
}>();

const router = useRouter();
const { $gettext } = useGettext();
const confirm = useConfirm();
const { isEditorDirty } = useEditorDirtyState();

function onAddChild() {
    function doNavigate() {
        navigateToSchemeOrConcept(router, NEW_CONCEPT, {
            scheme: node.data.schemeId,
            parent: node.data.id,
            parentTreeKey: node.key,
        });
    }

    if (isEditorDirty.value) {
        confirm.require({
            group: "unsaved-changes",
            header: $gettext("Unsaved Changes"),
            message: $gettext(
                "You have unsaved changes that will be discarded. Do you want to continue?",
            ),
            acceptProps: {
                label: $gettext("Discard Changes"),
                severity: DANGER,
            },
            rejectProps: {
                label: $gettext("Keep Editing"),
                severity: SECONDARY,
                outlined: true,
            },
            accept: doNavigate,
        });
    } else {
        doNavigate();
    }
}
</script>

<template>
    <Button
        v-tooltip="{
            value: addChildLabel,
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
