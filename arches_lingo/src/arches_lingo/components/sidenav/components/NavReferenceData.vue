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
        key: "contributors",
        label: $gettext("Contributors"),
        icon: "fa fa-user",
        route: { name: routeNames.root },
        disabled: true,
    },
    {
        key: "sources",
        label: $gettext("Sources"),
        icon: "pi pi-bookmark-fill",
        route: { name: routeNames.root },
        disabled: true,
    },
    {
        key: "controlled_lists",
        label: $gettext("Controlled List Manager"),
        icon: "fa fa-list",
        route: { name: routeNames.root },
        disabled: true,
        showIconIfCollapsed: true,
    },
];

const navSection = ref<SideNavMenuItem>(props.item);
navSection.value.items = children;
</script>

<template>
    <SideNavSection :item="navSection"></SideNavSection>
</template>
