<script setup lang="ts">
import { storeToRefs } from "pinia";
import Divider from "primevue/divider";

import { useAppSettingsStore } from "@/arches_lingo/stores/useAppSettingsStore.ts";
import ThemeSelector from "@/arches_lingo/components/header/PageHeader/components/UserInteraction/components/UserInteractionMenu/components/ThemeSelector.vue";
import UserInteractionTools from "@/arches_lingo/components/header/PageHeader/components/UserInteraction/components/UserInteractionMenu/components/UserInteractionTools.vue";

defineProps<{
    displayName: string;
    email: string;
}>();

const { archesVersion, lingoVersion } = storeToRefs(useAppSettingsStore());
</script>

<template>
    <div class="user-interaction-menu">
        <div class="display-name">{{ displayName }}</div>
        <div class="email">{{ email }}</div>

        <Divider />

        <div class="user-interactions">
            <ThemeSelector />
            <UserInteractionTools />
        </div>

        <Divider />

        <span class="application-version"
            >Lingo v{{ lingoVersion }} | Arches v{{ archesVersion }}</span
        >
    </div>
</template>

<style scoped>
.application-version {
    font-size: var(--p-lingo-font-size-xsmall);
    color: var(--p-text-muted-color);
}
.display-name {
    font-size: var(--p-lingo-font-size-normal);
    font-weight: 400;
}
.email {
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-text-muted-color);
    margin-top: 0.25rem;
}
.user-interaction-menu {
    font-family: var(--p-lingo-font-family);
    width: 20rem;
    height: 100%;
}

.user-interactions {
    display: flex;
    justify-content: space-between;
    flex-direction: column;
    gap: 1rem;
}
</style>
