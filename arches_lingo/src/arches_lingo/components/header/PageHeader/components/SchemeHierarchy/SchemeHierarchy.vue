<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import HierarchyOverlay from "@/arches_lingo/components/header/PageHeader/components/SchemeHierarchy/components/HierarchyOverlay.vue";
const { $gettext } = useGettext();

const showHierarchy = ref(false);

function activateHierarchyOverlay() {
    showHierarchy.value = true;
}
</script>

<template>
    <div>
        <Button
            icon="pi pi-globe"
            variant="text"
            class="explore-button"
            :label="$gettext('Explore')"
            @click="activateHierarchyOverlay"
        />
        <HierarchyOverlay v-model:show-hierarchy="showHierarchy" />
    </div>
</template>

<style scoped>
.explore-button {
    color: var(--p-menubar-text-color) !important;
}

.explore-button:hover {
    background: var(--p-button-primary-hover-background) !important;
}
</style>
