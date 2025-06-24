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
        key: "profile",
        label: $gettext("Profile"),
        icon: "pi pi-shield",
        route: { name: routeNames.root },
        disabled: true,
        showIconIfCollapsed: true,
    },
    {
        key: "system_settings",
        label: $gettext("System Settings"),
        icon: "pi pi-cog",
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
