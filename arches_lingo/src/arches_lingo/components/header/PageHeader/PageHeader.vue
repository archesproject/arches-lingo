<script setup lang="ts">
import { useTemplateRef, watch } from "vue";
import { useGettext } from "vue3-gettext";

import { ToggleButton } from "primevue";
import Button from "primevue/button";
import Menubar from "primevue/menubar";
import Popover from "primevue/popover";

import ArchesLingoBadge from "@/arches_lingo/components/header/PageHeader/components/ArchesLingoBadge.vue";
import LanguageSelector from "@/arches_lingo/components/header/PageHeader/components/LanguageSelector.vue";
import NotificationInteraction from "@/arches_lingo/components/header/PageHeader/components/NotificationsInteraction/NotificationInteraction.vue";
import PageHelp from "@/arches_lingo/components/header/PageHeader/components/PageHelp/PageHelp.vue";
import SearchDialog from "@/arches_lingo/components/header/PageHeader/components/SearchDialog.vue";
import UserInteraction from "@/arches_lingo/components/header/PageHeader/components/UserInteraction/UserInteraction.vue";

const { $gettext } = useGettext();

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

            <Popover
                ref="overlayPanel"
                show-close-icon
                :pt="{
                    root: { class: 'overlay-panel-popover-root' },
                    content: { class: 'overlay-panel-popover-content' },
                }"
            >
                <div class="overlay-panel-items">
                    <div class="overlay-panel-item">
                        <UserInteraction />
                    </div>
                    <div class="overlay-panel-item">
                        <LanguageSelector />
                    </div>
                    <div class="overlay-panel-item">
                        <NotificationInteraction />
                    </div>
                    <div class="overlay-panel-item">
                        <PageHelp />
                    </div>
                </div>
            </Popover>
        </template>
    </Menubar>
</template>

<style scoped>
.explore-button {
    background: var(--p-menubar-background) !important;
    border: none !important;
    color: var(--p-menubar-text-color) !important;
    padding: var(--p-button-padding-y) var(--p-button-padding-x);
    height: 3rem;
    border-radius: 0;
}

:deep(.explore-button .p-togglebutton-content),
:deep(.explore-button .p-togglebutton-label),
:deep(.explore-button .p-togglebutton-icon) {
    background: transparent !important;
    color: var(--p-menubar-text-color) !important;
    font-size: 0.875rem;
}

.explore-button:not(.p-togglebutton-checked):hover {
    background: var(--p-button-primary-hover-background) !important;
}

.explore-button.p-togglebutton-checked,
.explore-button.p-togglebutton-checked * {
    background: var(--p-button-primary-hover-background) !important;
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
}

.overlay-panel-button {
    display: none;
    color: var(--p-menubar-color) !important;
}

.overlay-panel-items {
    display: flex;
    flex-direction: column;
    align-items: stretch;
}

:deep(.overlay-panel-item .p-button) {
    width: 100%;
    justify-content: flex-start;
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
