<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import PageHelpPanel from "@/arches_lingo/components/header/PageHeader/components/PageHelp/components/PageHelpPanel.vue";

const { $gettext } = useGettext();

const shouldShowPageHelpPanel = ref(false);

function activateHierarchyOverlay() {
    shouldShowPageHelpPanel.value = true;
}
</script>

<template>
    <div>
        <Button
            icon="pi pi-question-circle"
            variant="text"
            class="page-help-button"
            :label="$gettext('Help')"
            @click="activateHierarchyOverlay"
        />
        <PageHelpPanel
            v-model:should-show-page-help-panel="shouldShowPageHelpPanel"
        />
    </div>
</template>

<style scoped>
.page-help-button {
    color: var(--p-menubar-text-color) !important;
    height: 3rem;
}

.page-help-button:hover {
    background: var(--p-button-primary-hover-background) !important;
}
</style>
