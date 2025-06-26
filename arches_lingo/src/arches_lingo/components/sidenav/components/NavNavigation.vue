<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import { routeNames } from "@/arches_lingo/routes.ts";
import SideNavSection from "@/arches_lingo/components/sidenav/components/SideNavSection.vue";

import type { SideNavMenuItem } from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();

const props = defineProps<{
    item: SideNavMenuItem;
}>();

const children = <SideNavMenuItem[]>[
    {
        key: "dashboard",
        label: $gettext("Dashboard"),
        icon: "pi pi-home",
        route: { name: routeNames.root },
        disabled: true,
        showIconIfCollapsed: true,
    },
    {
        key: "advanced_search",
        label: $gettext("Advanced Search"),
        icon: "pi pi-search",
        route: { name: routeNames.advancedSearch },
        showIconIfCollapsed: true,
    },
];

const navSection = ref<SideNavMenuItem>(props.item);
navSection.value.items = children;
</script>

<template>
    <SideNavSection :item="navSection"></SideNavSection>
</template>
