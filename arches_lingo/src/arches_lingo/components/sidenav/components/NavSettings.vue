<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import { routeNames } from "@/arches_lingo/routes.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";
import SideNavSection from "@/arches_lingo/components/sidenav/components/SideNavSection.vue";

import type { SideNavMenuItem } from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();
const { isResourceEditor } = useUserStore();

const props = defineProps<{
    item: SideNavMenuItem;
}>();

const children: SideNavMenuItem[] = [
    {
        key: "profile",
        label: $gettext("Profile"),
        icon: "pi pi-user",
        route: { name: routeNames.profile },
        showIconIfCollapsed: true,
    },
];

if (isResourceEditor) {
    children.push({
        key: "tasks",
        label: $gettext("My Tasks"),
        icon: "pi pi-list",
        route: { name: routeNames.tasks },
        showIconIfCollapsed: true,
    });
}

children.push({
    key: "system_settings",
    label: $gettext("System Settings"),
    icon: "pi pi-cog",
    route: { name: routeNames.root },
    disabled: true,
    showIconIfCollapsed: true,
});

const navSection = ref<SideNavMenuItem>(props.item);
navSection.value.items = children;
</script>

<template>
    <SideNavSection :item="navSection"></SideNavSection>
</template>
