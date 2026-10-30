<script setup lang="ts">
import { computed, nextTick, ref, useId, useTemplateRef, watch } from "vue";
import { useRoute } from "vue-router";
import { useGettext } from "vue3-gettext";

import { ToggleButton } from "primevue";
import Button from "primevue/button";
import Drawer from "primevue/drawer";
import Menubar from "primevue/menubar";
import Popover from "primevue/popover";

import ArchesLingoBadge from "@/arches_lingo/components/header/PageHeader/components/ArchesLingoBadge.vue";
import LanguageSelector from "@/arches_lingo/components/header/PageHeader/components/LanguageSelector.vue";
import NotificationInteraction from "@/arches_lingo/components/header/PageHeader/components/NotificationsInteraction/NotificationInteraction.vue";
import PageHelp from "@/arches_lingo/components/header/PageHeader/components/PageHelp/PageHelp.vue";
import SearchDialog from "@/arches_lingo/components/header/PageHeader/components/SearchDialog.vue";
import UserInteraction from "@/arches_lingo/components/header/PageHeader/components/UserInteraction/UserInteraction.vue";
import SideNavLinks from "@/arches_lingo/components/sidenav/components/SideNavLinks.vue";

import { focusFirstFocusableElement } from "@/arches_lingo/utils.ts";

import type { ComponentPublicInstance } from "vue";

const { $gettext } = useGettext();
const route = useRoute();

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
const overlayPanelItems = useTemplateRef<HTMLElement>("overlayPanelItems");
const isOverlayPanelVisible = ref(false);

function onOverlayPanelShow() {
    isOverlayPanelVisible.value = true;
    focusFirstFocusableElement(overlayPanelItems.value);
}

const mobileNavButton =
    useTemplateRef<ComponentPublicInstance>("mobileNavButton");
const mobileNavTitleId = useId();
const isMobileNavVisible = ref(false);
const wasMobileNavClosedByNavigation = ref(false);
const mobileNavLabel = computed(() =>
    $gettext("%{appName} navigation", { appName: $gettext("Lingo") }),
);

watch(
    () => route.path,
    () => {
        if (isMobileNavVisible.value) {
            wasMobileNavClosedByNavigation.value = true;
            isMobileNavVisible.value = false;
        }
    },
);

async function onMobileNavAfterHide() {
    if (wasMobileNavClosedByNavigation.value) {
        wasMobileNavClosedByNavigation.value = false;
        return;
    }
    // PrimeVue Drawer doesn't return focus to its trigger.
    await nextTick();
    (mobileNavButton.value?.$el as HTMLElement | undefined)?.focus();
}
</script>

<template>
    <header class="page-header">
        <!-- With no model, Menubar still renders an empty role="menubar" list
         with tabindex="0"; hiding it removes that empty tab stop. -->
        <Menubar :pt="{ rootList: { style: { display: 'none' } } }">
            <template #start>
                <Button
                    ref="mobileNavButton"
                    icon="pi pi-bars"
                    class="mobile-nav-button p-button-text"
                    :aria-label="mobileNavLabel"
                    aria-haspopup="dialog"
                    :aria-expanded="isMobileNavVisible"
                    @click="isMobileNavVisible = true"
                />
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
                    :aria-label="$gettext('Menu')"
                    aria-haspopup="dialog"
                    :aria-expanded="isOverlayPanelVisible"
                    @click="overlayPanel?.toggle($event)"
                />

                <Popover
                    ref="overlayPanel"
                    show-close-icon
                    :pt="{
                        root: { class: 'overlay-panel-popover-root' },
                        content: { class: 'overlay-panel-popover-content' },
                    }"
                    @show="onOverlayPanelShow"
                    @hide="isOverlayPanelVisible = false"
                >
                    <div
                        ref="overlayPanelItems"
                        class="overlay-panel-items"
                    >
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
    </header>

    <Drawer
        v-model:visible="isMobileNavVisible"
        :header="mobileNavLabel"
        :pt="{
            root: {
                class: 'mobile-nav-drawer',
                role: 'dialog',
                'aria-labelledby': mobileNavTitleId,
            },
            title: { id: mobileNavTitleId },
        }"
        @after-hide="onMobileNavAfterHide"
    >
        <SideNavLinks :is-expanded="true" />
    </Drawer>
</template>

<style scoped>
.explore-button {
    background: var(--p-lingo-navigation-bar-background) !important;
    border: none !important;
    color: inherit !important;
    padding: var(--p-button-padding-y) var(--p-button-padding-x);
    height: 3rem;
    border-radius: 0;
}

:deep(.explore-button .p-togglebutton-content),
:deep(.explore-button .p-togglebutton-label),
:deep(.explore-button .p-togglebutton-icon) {
    background: transparent !important;
    color: inherit !important;
    font-size: 0.875rem;
}

.explore-button:not(.p-togglebutton-checked):hover {
    background: var(--p-lingo-navigation-bar-hover-background) !important;
}

.explore-button.p-togglebutton-checked,
.explore-button.p-togglebutton-checked * {
    background: var(--p-lingo-navigation-bar-hover-background) !important;
}

.p-menubar {
    border-radius: 0;
    border-inline-start: 0;
    border-inline-end: 0;
    padding-inline-start: 1rem;
    border-bottom: 0.125rem solid var(--p-primary-950) !important;
    min-height: 3.125rem;
    flex-wrap: wrap;
    border: none;
}

:deep(.p-menubar-start) {
    gap: var(--p-menubar-gap);
}

.end-items {
    display: flex;
    align-items: center;
}

.overlay-panel-button,
.mobile-nav-button {
    display: none;
    color: var(--p-lingo-navigation-bar-color) !important;
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
    .overlay-panel-button,
    .mobile-nav-button {
        display: inline-flex !important;
    }
}

/* Icon-only on narrow screens; the text stays in the accessible name. */
@media screen and (max-width: 480px) {
    :deep(.explore-button .p-togglebutton-label),
    :deep(.basic-search-button .p-button-label),
    :deep(.lingo-title) {
        position: absolute;
        width: 1px;
        height: 1px;
        margin: -1px;
        padding: 0;
        overflow: hidden;
        clip: rect(0 0 0 0);
        white-space: nowrap;
        border: 0;
    }
}
</style>

<!-- NOT scoped because the drawer is appended to <body> -->
<style>
.mobile-nav-drawer {
    background: var(--p-surface-950) !important;
    color: var(--p-lingo-navigation-bar-color) !important;
}

.mobile-nav-drawer .p-drawer-content {
    padding: 0;
}
</style>
