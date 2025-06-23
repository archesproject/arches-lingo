<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import { routeNames } from "@/arches_lingo/routes.ts";
import SideNavSection from "@/arches_lingo/components/sidenav/SideNavSection.vue";

import type { SideNavMenuItem } from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();

const props = defineProps<{
    item: SideNavMenuItem;
}>();

const children = <SideNavMenuItem[]>[
    {
        key: "schemes",
        label: $gettext("Schemes & Concepts"),
        icon: "pi pi-lightbulb",
        route: { name: routeNames.schemes },
        showIconIfCollapsed: true,
    },
    {
        key: "places",
        label: $gettext("Places"),
        icon: "pi pi-globe",
        route: { name: routeNames.root },
        disabled: true,
        showIconIfCollapsed: false,
    },
    {
        key: "people",
        label: $gettext("People"),
        icon: "pi pi-user",
        route: { name: routeNames.root },
        disabled: true,
        showIconIfCollapsed: false,
    },
    {
        key: "groups",
        label: $gettext("Groups"),
        icon: "pi pi-users",
        route: { name: routeNames.root },
        disabled: true,
        showIconIfCollapsed: false,
    },
    {
        key: "periods",
        label: $gettext("Periods"),
        icon: "fa fa-hourglass-start",
        route: { name: routeNames.root },
        disabled: true,
        showIconIfCollapsed: false,
    },
];

const navSection = ref<SideNavMenuItem>(props.item);
navSection.value.items = children;
</script>

<template>
    <SideNavSection :item="navSection"></SideNavSection>
</template>
