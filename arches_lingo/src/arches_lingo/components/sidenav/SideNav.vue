<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import { routeNames } from "@/arches_lingo/routes.ts";

import Button from "primevue/button";
import PanelMenu from "primevue/panelmenu";

import type { MenuItem } from "primevue/menuitem";

const { $gettext } = useGettext();

// const expandedKeys = ref<Record<string, boolean>>({});
const isExpanded = ref(false);
const items = ref<MenuItem[]>([
    {
        key: "navigation",
        label: $gettext("Navigation"),
        class: "nav-heading",
        separator: true,
        visible: showHeadings,
    },
    {
        key: "dashboard",
        label: $gettext("Dashboard"),
        icon: "fa fa-home",
        route: { name: routeNames.root },
        disabled: true,
    },
    {
        key: "advanced_search",
        label: $gettext("Advanced Search"),
        icon: "pi pi-search",
        route: { name: routeNames.advancedSearch },
    },
    {
        key: "editors",
        label: $gettext("Authority Editors"),
        class: "nav-heading",
        separator: true,
        visible: showHeadings,
    },
    {
        key: "schemes",
        label: $gettext("Schemes"),
        icon: "pi pi-lightbulb",
        route: { name: routeNames.schemes },
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
                <router-link
                    v-if="item.route"
                    v-slot="{ href, navigate }"
                    :to="item.route"
                    custom
                >
                    <a
                        v-tooltip="{
                            value: item.label,
                            pt: { text: { style: { fontFamily: '-' } } },
                        }"
                        :href="href"
                        class="nav-button p-button"
                        @click="navigate"
                    >
                        <i :class="item.icon"></i>
                        <span v-if="isExpanded">{{ item.label }}</span>
                    </a>
                </router-link>
                <a
                    v-else
                    class="nav-button p-button"
                >
                    <i :class="item.icon"></i>
                    <span v-if="isExpanded">{{ item.label }}</span>
                    <span
                        v-if="item.items"
                        class="pi pi-angle-down text-primary ml-auto"
                    />
                </a>
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
