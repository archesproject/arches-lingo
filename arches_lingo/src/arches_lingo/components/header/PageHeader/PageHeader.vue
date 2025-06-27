<script setup lang="ts">
import { ref } from "vue";

import Button from "primevue/button";
import Menubar from "primevue/menubar";
import OverlayPanel from "primevue/overlaypanel";

import ArchesLingoBadge from "@/arches_lingo/components/header/PageHeader/components/ArchesLingoBadge.vue";
import LanguageSelector from "@/arches_lingo/components/header/PageHeader/components/LanguageSelector.vue";
import NotificationInteraction from "@/arches_lingo/components/header/PageHeader/components/NotificationsInteraction/NotificationInteraction.vue";
import PageHelp from "@/arches_lingo/components/header/PageHeader/components/PageHelp/PageHelp.vue";
import SchemeHierarchy from "@/arches_lingo/components/header/PageHeader/components/SchemeHierarchy/SchemeHierarchy.vue";
import SearchDialog from "@/arches_lingo/components/header/PageHeader/components/SearchDialog.vue";
import UserInteraction from "@/arches_lingo/components/header/PageHeader/components/UserInteraction/UserInteraction.vue";

const props = defineProps<{
    isNavExpanded: boolean;
}>();

const mobileMenu = ref();
</script>

<template>
    <Menubar>
        <template #start>
            <ArchesLingoBadge v-if="!props.isNavExpanded" />
            <SchemeHierarchy />
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
                class="mobile-menu-button p-button-text"
                @click="mobileMenu?.toggle($event)"
            />
            <OverlayPanel
                ref="mobileMenu"
                show-close-icon
            >
                <div class="mobile-menu-items">
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
.mobile-menu-button {
    display: none;
    color: var(--p-menubar-color) !important;
}

@media screen and (max-width: 960px) {
    .end-items {
        display: none !important;
    }
    .mobile-menu-button {
        display: inline-flex !important;
    }
}
</style>
