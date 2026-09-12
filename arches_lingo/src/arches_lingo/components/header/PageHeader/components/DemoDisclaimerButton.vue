<script setup lang="ts">
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import { useDemoDisclaimer } from "@/arches_lingo/composables/useDemoDisclaimer.ts";

const { $gettext } = useGettext();

const { isDemoDisclaimerEnabled, openDemoDisclaimer } = useDemoDisclaimer();
</script>

<template>
    <Button
        v-if="isDemoDisclaimerEnabled"
        icon="pi pi-info-circle"
        variant="text"
        class="demo-disclaimer-button"
        :label="$gettext('Demo Info')"
        @click="openDemoDisclaimer"
    />
</template>

<style scoped>
.demo-disclaimer-button {
    color: var(--p-menubar-text-color) !important;
    height: 3rem;
    border-radius: 0;
    font-size: 0.875rem;
}

.demo-disclaimer-button:hover {
    background: var(--p-button-primary-hover-background) !important;
}
</style>
