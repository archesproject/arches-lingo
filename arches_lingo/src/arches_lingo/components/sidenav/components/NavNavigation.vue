<script setup lang="ts">
import { onMounted } from "vue";
import { useGettext } from "vue3-gettext";

import { routeNames } from "@/arches_lingo/routes.ts";

import type { Component } from "vue";
import type { MenuItem } from "primevue/menuitem";

import SideNavSection from "@/arches_lingo/components/sidenav/SideNavSection.vue";

const { $gettext } = useGettext();

const props = defineProps<{
    item: {
        component: Component;
        key: string;
        label?: string;
        icon?: string;
        route?: string;
        items?: MenuItem[];
    };
}>();

const children = <MenuItem[]>[
    {
        key: "home",
        label: $gettext("Home"),
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
];

onMounted(() => {
    if (props.item.items) {
        const existingKeys = new Set(props.item.items.map((item) => item.key));
        const newChildren = children.filter(
            (child) => child.key && !existingKeys.has(child.key),
        );

        if (newChildren.length > 0) {
            props.item.items.push(...newChildren);
        }
    }
});
</script>

<template>
    <SideNavSection :item="props.item"></SideNavSection>
</template>
