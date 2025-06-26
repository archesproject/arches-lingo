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
    <aside class="sidenav">
        <Button
            :key="buttonKey"
            v-tooltip.bottom="{
                value: $gettext('Expand navigation'),
                disabled: isNavExpanded,
                pt: {
                    root: { style: { marginInlineStart: '6rem' } },
                    text: { style: { fontFamily: '--p-lingo-font-family' } },
                    arrow: { style: { display: 'none' } },
                },
            }"
            class="nav-button"
            :aria-label="$gettext('Expand navigation')"
            @click="toggleAll"
        >
            <i class="pi pi-bars toggle-icon"></i>

            <ArchesLingoBadge
                v-if="isNavExpanded"
                :is-link="false"
                style="margin-inline-start: 3rem; margin-inline-end: 1rem"
            />
        </Button>
        <PanelMenu
            :model="items"
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
    background: var(--p-primary-950);
}

.p-button {
    height: 2.5rem;
    font-size: var(--p-lingo-font-size-large);
    background: var(--p-primary-950) !important;
    border: none !important;
    border-radius: 0;
}

.expanded {
    min-width: 12rem;
}

:deep(.p-panelmenu-panel) {
    padding: 0;
    border-style: none;
    border-radius: 0 !important;
}

:deep(.nav-button) {
    height: 3.125rem;
    width: 100%;
    border-radius: 0;
    text-decoration: none;
    justify-content: flex-start;
    font-size: var(--p-lingo-font-size-xsmall);

    i {
        font-size: var(--p-lingo-font-size-medium);
    }
}

@media screen and (max-width: 960px) {
    .sidenav {
        display: none;
    }
}
</style>
