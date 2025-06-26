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
        style="min-width: 32rem"
        :header="$gettext('Explore Hierarchies')"
        :pt="{
            content: {
                style: {
                    padding: '0',
                    display: 'flex',
                    flexDirection: 'column',
                    fontFamily: 'var(--p-lingo-font-family)',
                },
            },
            header: {
                style: {
                    display: 'flex',
                    justifyContent: 'space-between',
                    backgroundColor: 'var(--p-form-field-filled-background)',
                    paddingBottom: '0.5rem',
                    fontFamily: 'var(--p-lingo-font-family)',
                },
            },
        }"
    >
        <ConceptTree :key="conceptTreeKey" />
    </Drawer>
</template>

<style scoped></style>
