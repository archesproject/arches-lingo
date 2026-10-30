<script setup lang="ts">
import { computed, markRaw, provide, toRef } from "vue";
import { useGettext } from "vue3-gettext";

import NavNavigation from "@/arches_lingo/components/sidenav/components/NavNavigation.vue";
import NavReferenceData from "@/arches_lingo/components/sidenav/components/NavReferenceData.vue";
import NavSettings from "@/arches_lingo/components/sidenav/components/NavSettings.vue";

import type { SideNavMenuItem } from "@/arches_lingo/types.ts";

const props = defineProps<{
    isExpanded: boolean;
}>();

const { $gettext } = useGettext();

provide("isNavExpanded", toRef(props, "isExpanded"));

const items = computed<SideNavMenuItem[]>(() => [
    {
        component: markRaw(NavNavigation),
        key: "navigation",
        label: $gettext("Navigation"),
        items: [],
    },
    {
        component: markRaw(NavReferenceData),
        key: "reference-data",
        label: $gettext("Reference Data"),
        items: [],
    },
    {
        component: markRaw(NavSettings),
        key: "settings",
        label: $gettext("Settings"),
        items: [],
    },
]);
</script>

<template>
    <nav
        class="sidenav-links"
        :class="{ expanded: props.isExpanded }"
        :aria-label="$gettext('Main')"
    >
        <component
            :is="item.component"
            v-for="item in items"
            :key="item.key"
            :item="item"
        />
    </nav>
</template>

<style scoped>
.sidenav-links {
    display: flex;
    flex-direction: column;
    width: 100%;
    min-width: 3rem;
    transition: min-width 0.3s ease-in-out;
    border-right: 0.125rem solid var(--p-primary-950);
    gap: 0.1rem;
    background-color: var(--p-surface-950);
}

.sidenav-links.expanded {
    min-width: 16rem;
}

:deep(.p-button) {
    background-color: var(--p-primary-950) !important;
    border-color: var(--p-primary-950) !important;
    color: var(--p-lingo-navigation-bar-color) !important;
}

:deep(.p-button):hover {
    background: var(--p-lingo-navigation-bar-hover-background) !important;
}

:deep(.nav-button) {
    height: 2.75rem;
    width: 100%;
    border-radius: 0;
    text-decoration: none;
    justify-content: flex-start;
    font-size: var(--p-lingo-font-size-xsmall);

    i {
        font-size: var(--p-lingo-font-size-xsmall);
        padding: 0rem 0rem 0rem 0.25rem;
    }
}
</style>
