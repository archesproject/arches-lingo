<script setup lang="ts">
import { markRaw, provide, ref } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import PanelMenu from "primevue/panelmenu";

import NavNavigation from "@/arches_lingo/components/sidenav/components/NavNavigation.vue";
import NavAuthorityEditors from "@/arches_lingo/components/sidenav/components/NavAuthorityEditors.vue";
import NavReferenceData from "@/arches_lingo/components/sidenav/components/NavReferenceData.vue";
import NavSettings from "@/arches_lingo/components/sidenav/components/NavSettings.vue";

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

function toggleAll() {
    isNavExpanded.value = !isNavExpanded.value;
}
</script>

<template>
    <aside class="sidenav">
        <Button
            v-tooltip="{
                value: $gettext('Expand navigation'),
                disabled: isNavExpanded,
                pt: {
                    text: { style: { fontFamily: '--p-lingo-font-family' } },
                },
            }"
            class="nav-button"
            :aria-label="$gettext('Expand navigation')"
            @click="toggleAll"
        >
            <i class="pi pi-bars toggle-icon"></i>
        </Button>
        <PanelMenu :model="items">
            <template #item="{ item }">
                <component
                    :is="item.component"
                    :item="item"
                    :nav-is-expanded="isNavExpanded"
                />
            </template>
        </PanelMenu>
    </aside>
</template>

<style scoped>
.sidenav {
    border-right: 1px solid var(--p-menubar-border-color);
    min-width: max-content;
}

.p-panelmenu {
    gap: 0;
}

:deep(.p-panelmenu-panel) {
    padding: 0;
    border-style: none;
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
