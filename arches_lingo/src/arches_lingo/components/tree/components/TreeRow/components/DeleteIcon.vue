<script setup lang="ts">
import { useRouter } from "vue-router";

import Button from "primevue/button";

const { deleteLabel } = defineProps<{
    deleteLabel: string;
}>();

const router = useRouter();

function onDeleteItem() {
    router.go(-1);
}
</script>

<template>
    <Button
        v-tooltip="{
            value: deleteLabel,
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
