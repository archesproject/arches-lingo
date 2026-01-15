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
                    style: { fontFamily: 'sans-serif' },
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
