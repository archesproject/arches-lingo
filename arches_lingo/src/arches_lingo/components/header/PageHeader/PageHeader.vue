<script setup lang="ts">
import { useTemplateRef, watch } from "vue";

import { ToggleButton } from "primevue";
import Menubar from "primevue/menubar";
import OverlayPanel from "primevue/overlaypanel";

import ArchesLingoBadge from "@/arches_lingo/components/header/PageHeader/components/ArchesLingoBadge.vue";
import LanguageSelector from "@/arches_lingo/components/header/PageHeader/components/LanguageSelector.vue";
import NotificationInteraction from "@/arches_lingo/components/header/PageHeader/components/NotificationsInteraction/NotificationInteraction.vue";
import PageHelp from "@/arches_lingo/components/header/PageHeader/components/PageHelp/PageHelp.vue";
import SearchDialog from "@/arches_lingo/components/header/PageHeader/components/SearchDialog.vue";
import UserInteraction from "@/arches_lingo/components/header/PageHeader/components/UserInteraction/UserInteraction.vue";

const shouldShowHierarchy = defineModel<boolean>({
    type: Boolean,
    required: true,
});

const props = defineProps<{
    isNavExpanded: boolean;
}>();

const emit = defineEmits<{
    (e: "shouldShowHierarchy", value: boolean): void;
}>();

watch(shouldShowHierarchy, (newValue) => {
    emit("shouldShowHierarchy", newValue);
});

const overlayPanel = useTemplateRef("overlayPanel");
</script>

<template>
    <Menubar>
        <template #start>
            <ArchesLingoBadge v-if="!props.isNavExpanded" />

            <ToggleButton
                v-model="shouldShowHierarchy"
                on-icon="pi pi-globe"
                off-icon="pi pi-globe"
                :on-label="$gettext('Explore')"
                :off-label="$gettext('Explore')"
                class="explore-button"
            />
            <SearchDialog />
        </template>
        <template #end>
            <div class="end-items">
                <UserInteraction />
                <LanguageSelector />
                <NotificationInteraction />
                <PageHelp />
            </div>
            <Button
                icon="pi pi-bars"
                class="overlay-panel-button p-button-text"
                @click="overlayPanel?.toggle($event)"
            />
            <OverlayPanel
                ref="overlayPanel"
                show-close-icon
            >
                <div class="overlay-panel-items">
                    <UserInteraction />
                    <LanguageSelector />
                    <NotificationInteraction />
                    <PageHelp />
                </div>
            </OverlayPanel>
        </template>
    </Menubar>
</template>

<style scoped>
.explore-button,
.explore-button * {
    background: var(--p-menubar-background) !important;
    border: none !important;
    color: var(--p-menubar-text-color) !important;
}

.explore-button.p-togglebutton-checked,
.explore-button.p-togglebutton-checked * {
    background: var(--p-togglebutton-checked-background) !important;
    color: var(--p-togglebutton-checked-color) !important;
}

.p-menubar {
    border-radius: 0;
    border-inline-start: 0;
    border-inline-end: 0;
    padding-inline-start: 1rem;
    border-bottom: 0.125rem solid var(--p-primary-950) !important;
    height: 3.125rem;
    border: none;
}
:deep(.p-menubar-start) {
    gap: var(--p-menubar-gap);
}

.end-items {
    display: flex;
    align-items: center;
    gap: var(--p-menubar-gap);
}
.overlay-panel-button {
    display: none;
    color: var(--p-menubar-color) !important;
}

@media screen and (max-width: 960px) {
    .end-items {
        display: none !important;
    }
    .overlay-panel-button {
        display: inline-flex !important;
    }
}
</style>
