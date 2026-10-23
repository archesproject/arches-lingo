<script setup lang="ts">
import Button from "primevue/button";

const {
    title,
    icon,
    showPanelLabel,
    hidePanelLabel,
    showPanelIcon,
    hidePanelIcon,
    canTogglePanel = true,
} = defineProps<{
    title: string;
    icon: string;
    showPanelLabel: string;
    hidePanelLabel: string;
    showPanelIcon: string;
    hidePanelIcon: string;
    canTogglePanel?: boolean;
}>();

const isPanelVisible = defineModel<boolean>("isPanelVisible", {
    required: true,
});

function togglePanel(): void {
    isPanelVisible.value = !isPanelVisible.value;
}
</script>

<template>
    <div class="panel-toggle-header">
        <h2 class="title">
            <i
                :class="icon"
                aria-hidden="true"
            />
            <span>{{ title }}</span>
        </h2>
        <Button
            v-if="canTogglePanel"
            class="panel-toggle"
            size="small"
            :label="isPanelVisible ? hidePanelLabel : showPanelLabel"
            :icon="isPanelVisible ? hidePanelIcon : showPanelIcon"
            @click="togglePanel"
        />
    </div>
</template>

<style scoped>
.panel-toggle-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    row-gap: 0.5rem;
    min-height: 3rem;
    padding: 0.375rem 1rem;
    background: var(--p-header-toolbar-background);
    border-block-end: 0.0625rem solid var(--p-header-toolbar-border);
    flex-shrink: 0;
    box-sizing: border-box;
}

.panel-toggle-header .title {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    margin: 0;
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-text-color);
}

.panel-toggle-header .title .pi {
    font-size: var(--p-lingo-font-size-medium);
}

/* The toolbar's own button look, which PrimeVue's button theme would otherwise
   override. */
.panel-toggle-header .panel-toggle {
    font-size: var(--p-lingo-font-size-small) !important;
    font-weight: var(--p-lingo-font-weight-normal) !important;
    border-radius: 0.125rem !important;
    background: var(--p-header-button-background) !important;
    color: var(--p-header-button-color) !important;
    border-color: var(--p-header-button-border) !important;
    border-style: solid !important;
    border-width: 0.0625rem !important;
}

.panel-toggle-header .panel-toggle:hover {
    background: var(--p-highlight-background) !important;
}
</style>
