<script setup lang="ts">
import { markRaw, provide, ref } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import PanelMenu from "primevue/panelmenu";

import NavNavigation from "@/arches_lingo/components/sidenav/components/NavNavigation.vue";
import NavAuthorityEditors from "@/arches_lingo/components/sidenav/components/NavAuthorityEditors.vue";
import NavReferenceData from "@/arches_lingo/components/sidenav/components/NavReferenceData.vue";
import NavSettings from "@/arches_lingo/components/sidenav/components/NavSettings.vue";

import ArchesLingoBadge from "@/arches_lingo/components/header/PageHeader/components/ArchesLingoBadge.vue";

import type { SideNavMenuItem } from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();

const isNavExpanded = ref(false);
provide("isNavExpanded", isNavExpanded);

const items = ref<SideNavMenuItem[]>([
    {
        component: markRaw(NavNavigation),
        key: "navigation",
        label: $gettext("Navigation"),
        items: [],
    },
    {
        component: markRaw(NavAuthorityEditors),
        key: "editors",
        label: $gettext("Authority Editors"),
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

const buttonKey = ref(0);

function toggleAll() {
    isNavExpanded.value = !isNavExpanded.value;
    emit("update:isNavExpanded", isNavExpanded.value);

    buttonKey.value += 1; // Force re-render of the button to remove tooltip
}

const emit = defineEmits(["update:isNavExpanded"]);
</script>

<template>
    <aside
        class="sidenav"
        :class="{ expanded: isNavExpanded }"
    >
        <Button
            :key="buttonKey"
            v-tooltip.bottom="{
                value: $gettext('Expand navigation'),
                disabled: isNavExpanded,
                showDelay: 300,
                pt: {
                    root: { style: { marginInlineStart: '3rem' } },
                    text: {
                        style: { fontFamily: 'var(--p-lingo-font-family)' },
                    },
                    arrow: { style: { display: 'none' } },
                },
            }"
            class="nav-button"
            :class="{ expanded: isNavExpanded }"
            :aria-label="$gettext('Expand navigation')"
            @click="toggleAll"
        >
            <i
                v-if="!isNavExpanded"
                class="pi pi-bars toggle-icon"
            />

            <ArchesLingoBadge
                v-if="isNavExpanded"
                :is-link="false"
            />
        </Button>
        <PanelMenu
            :model="items"
            class="sidenav-panelmenu"
            :class="{ expanded: isNavExpanded }"
        >
            <template #item="{ item }">
                <component
                    :is="item.component"
                    :item="item"
                />
            </template>
        </PanelMenu>
    </aside>
</template>

<style scoped>
.sidenav {
    width: 3rem;
    background: var(--p-primary-950);
    border-right: 0.125rem solid var(--p-primary-950);
    transition: width 0.3s ease-in-out;
}

.sidenav.expanded {
    width: 16rem;
}

.p-button {
    height: 2.5rem;
    font-size: var(--p-lingo-font-size-large);
    background: var(--p-primary-950) !important;
    border-radius: 0;
    border: none;
}

.sidenav-panelmenu {
    width: 100%;
    min-width: 3rem;
    transition: min-width 0.3s ease-in-out;
    border-right: 0.125rem solid var(--p-primary-950);
    gap: 0.1rem;
    background-color: var(--p-surface-950);
}

.sidenav-panelmenu.expanded {
    min-width: 16rem;
}

.nav-button {
    border: 0 !important;
    border-bottom: 0.125rem solid var(--p-primary-950) !important;
    cursor: pointer;
}

.nav-button.expanded {
    background: var(--p-menubar-background) !important;
    padding-inline-start: 0.6rem;
}

.nav-button:hover {
    background: var(--p-button-primary-hover-background) !important;
}

:deep(.p-button) {
    background-color: var(--p-primary-950) !important;
    border-color: var(--p-primary-950) !important;
    color: var(--p-menubar-color) !important;
}
:deep(.p-button):hover {
    background: var(--p-button-primary-hover-background) !important;
}

:deep(.p-panelmenu-panel) {
    padding: 0;
    border-style: none;
    border-radius: 0 !important;
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

@media screen and (max-width: 960px) {
    .sidenav {
        display: none;
    }
}
</style>
