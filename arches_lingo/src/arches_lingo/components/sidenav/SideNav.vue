<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import { routeNames } from "@/arches_lingo/routes.ts";

import Button from "primevue/button";
import PanelMenu from "primevue/panelmenu";

import type { MenuItem } from "primevue/menuitem";

const { $gettext } = useGettext();

const expandedKeys = ref<Record<string, boolean>>({});
const isExpanded = ref(false);
const items = ref<MenuItem[]>([
    {
        key: "navigation",
        label: $gettext("Navigation"),
        items: [
            {
                key: "home",
                label: $gettext("Home"),
                icon: "fa fa-home",
                route: { name: routeNames.root },
            } as MenuItem,
            {
                key: "advanced_search",
                label: $gettext("Advanced Search"),
                icon: "pi pi-search",
                route: { name: routeNames.advancedSearch },
            } as MenuItem,
        ],
    } as MenuItem,
    {
        key: "schemes",
        label: $gettext("Schemes"),
        icon: "pi pi-lightbulb",
        route: { name: routeNames.schemes },
    } as MenuItem,
]);

function toggleAll() {
    if (Object.keys(expandedKeys.value).length) collapseAll();
    else expandAll();
}

function toggleNode(node: MenuItem) {
    if (node.key && expandedKeys.value[node.key]) {
        collapseNode(node);
    } else {
        expandNode(node);
    }
}

function expandAll() {
    isExpanded.value = true;
    for (let node of items.value) {
        expandNode(node);
    }
    expandedKeys.value = { ...expandedKeys.value };
}

function collapseAll() {
    isExpanded.value = false;
    expandedKeys.value = {};
}

function expandNode(node: MenuItem) {
    if (node.key && node.items && node.items.length) {
        expandedKeys.value[node.key] = true;

        for (let child of node.items) {
            expandNode(child);
        }
    }
}

function collapseNode(node: MenuItem) {
    if (node.key && node.items && node.items.length) {
        expandedKeys.value[node.key] = false;

        for (let child of node.items) {
            collapseNode(child);
        }
    }
}
</script>

<template>
    <aside class="sidenav">
        <Button
            class="sidenav-header"
            @click="toggleAll"
        >
            <i class="pi pi-bars toggle-icon"></i>
            <!-- <span v-show="isExpanded" class="header-title">Navigation</span> -->
        </Button>
        <PanelMenu
            :model="items"
            :expanded-keys="expandedKeys"
        >
            <template #item="{ item }">
                <router-link
                    v-if="item.route"
                    v-slot="{ href, navigate }"
                    :to="item.route"
                    custom
                >
                    <a
                        :href="href"
                        @click="navigate"
                    >
                        <span :class="item.icon"></span>
                        <span v-if="isExpanded">{{ item.label }}</span>
                    </a>
                </router-link>
                <a
                    v-else
                    @click="toggleNode(item)"
                >
                    <span :class="item.icon"></span>
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

.lingo-link {
    min-height: var(--p-button-lg-icon-only-width);
    min-width: var(--p-button-lg-icon-only-width);
    border-radius: 0;
    font-size: var(--p-lingo-font-size-large);
    border-bottom: 0.1rem solid var(--p-button-outlined-primary-border-color);
}

@media screen and (max-width: 960px) {
    .sidenav {
        display: none;
    }
}
</style>
