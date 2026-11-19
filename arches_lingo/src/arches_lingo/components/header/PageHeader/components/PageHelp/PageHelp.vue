<script setup lang="ts">
import { nextTick, ref, useTemplateRef } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import PageHelpPanel from "@/arches_lingo/components/header/PageHeader/components/PageHelp/components/PageHelpPanel.vue";

import type { ComponentPublicInstance } from "vue";

const { $gettext } = useGettext();

const shouldShowPageHelpPanel = ref(false);
const helpButton = useTemplateRef<ComponentPublicInstance>("helpButton");

function activateHierarchyOverlay() {
    shouldShowPageHelpPanel.value = true;
}

// PrimeVue Drawer doesn't return focus to its trigger.
async function onPageHelpPanelAfterHide() {
    await nextTick();
    (helpButton.value?.$el as HTMLElement | undefined)?.focus();
}
</script>

<template>
    <div>
        <Button
            ref="helpButton"
            icon="pi pi-question-circle"
            variant="text"
            class="page-help-button"
            :label="$gettext('Help')"
            @click="activateHierarchyOverlay"
        />
        <PageHelpPanel
            v-model:should-show-page-help-panel="shouldShowPageHelpPanel"
            @after-hide="onPageHelpPanelAfterHide"
        />
    </div>
</template>

<style scoped>
.page-help-button {
    color: inherit !important;
    height: 3rem;
    border-radius: 0;
    font-size: 0.875rem;
}

.page-help-button:hover {
    background: var(--p-button-primary-hover-background) !important;
}
</style>
