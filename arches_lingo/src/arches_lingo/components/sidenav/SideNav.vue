<script setup lang="ts">
import { markRaw, provide, ref } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import PanelMenu from "primevue/panelmenu";

import NavNavigation from "@/arches_lingo/components/sidenav/components/NavNavigation.vue";
import NavAuthorityEditors from "@/arches_lingo/components/sidenav/components/NavAuthorityEditors.vue";
import NavReferenceData from "@/arches_lingo/components/sidenav/components/NavReferenceData.vue";
import NavSettings from "@/arches_lingo/components/sidenav/components/NavSettings.vue";

import type { MenuItem } from "primevue/menuitem";

const { $gettext } = useGettext();

// const expandedKeys = ref<Record<string, boolean>>({});
const isExpanded = ref(false);
const items = ref<MenuItem[]>([
    {
        component: markRaw(NavNavigation),
        key: "navigation",
        label: $gettext("Navigation"),
        visible: showHeadings,
        items: [],
    },
    {
        component: markRaw(NavAuthorityEditors),
        key: "editors",
        label: $gettext("Authority Editors"),
        visible: showHeadings,
        items: [],
    },
    {
        component: markRaw(NavReferenceData),
        key: "reference-data",
        label: $gettext("Reference Data"),
        visible: showHeadings,
        items: [],
    },
    {
        component: markRaw(NavSettings),
        key: "settings",
        label: $gettext("Settings"),
        visible: showHeadings,
        items: [],
    },
]);

function toggleAll() {
    isExpanded.value = !isExpanded.value;
}

function showHeadings() {
    return isExpanded.value;
}

// function toggleAll() {
//     if (Object.keys(expandedKeys.value).length) collapseAll();
//     else expandAll();
// }

// function toggleNode(node: MenuItem) {
//     if (node.key && expandedKeys.value[node.key]) {
//         collapseNode(node);
//     } else {
//         expandNode(node);
//     }
// }

// function expandAll() {
//     isExpanded.value = true;
//     for (let node of items.value) {
//         expandNode(node);
//     }
//     expandedKeys.value = { ...expandedKeys.value };
// }

// function collapseAll() {
//     isExpanded.value = false;
//     expandedKeys.value = {};
// }

// function expandNode(node: MenuItem) {
//     if (node.key && node.items && node.items.length) {
//         expandedKeys.value[node.key] = true;

//         for (let child of node.items) {
//             expandNode(child);
//         }
//     }
// }

// function collapseNode(node: MenuItem) {
//     if (node.key && node.items && node.items.length) {
//         expandedKeys.value[node.key] = false;

//         for (let child of node.items) {
//             collapseNode(child);
//         }
//     }
// }

provide("isExpanded", isExpanded);
</script>

<template>
    <aside class="sidenav">
        <Button
            v-tooltip="{
                value: $gettext('Expand navigation'),
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
                />
            </template>
        </PanelMenu>
    </aside>
</template>

<style scoped>
.sidenav {
    border-right: 1px solid var(--p-menubar-border-color);
}

.p-panelmenu {
    display: block;
}

:deep(.p-panelmenu-panel) {
    padding: 0;
    border-style: none;
}

.nav-button {
    min-height: var(--p-button-lg-icon-only-width);
    width: 100%;
    border-radius: 0;
    text-decoration: none;
    justify-content: flex-start;

    i {
        font-size: var(--p-lingo-font-size-large);
    }
}

@media screen and (max-width: 960px) {
    .sidenav {
        display: none;
    }
}
</style>
