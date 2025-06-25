<script setup lang="ts">
import { ref } from "vue";
import Drawer from "primevue/drawer";

import ConceptTree from "@/arches_lingo/components/tree/ConceptTree.vue";

const showHierarchy = defineModel("showHierarchy", {
    type: Boolean,
    default: false,
});

const conceptTreeKey = ref(0);
</script>

<template>
    <Drawer
        v-model:visible="showHierarchy"
        class="hierarchy-container"
        style="width: auto"
        :pt="{
            header: { style: { justifyContent: 'end' } },
            content: { style: { padding: '0' } },
        }"
    >
        <ConceptTree :key="conceptTreeKey" />
    </Drawer>
</template>

<style scoped>
.subheading {
    display: flex;
    margin: 0;
    gap: 0.5rem;
    height: 3rem;
    background: var(--p-button-secondary-background);
}

.subheading h2 {
    font-size: medium;
}

.toggle-hierarchy {
    border-radius: 0;
    border-inline-start: 0.06rem solid
        var(--p-button-secondary-active-border-color);
    border-inline-end: 0.06rem solid
        var(--p-button-secondary-active-border-color);
    font-size: var(--p-lingo-font-size-smallnormal);
}

:deep(.p-drawer-header) {
    justify-content: end;
}
</style>
