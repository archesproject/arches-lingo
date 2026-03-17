<script setup lang="ts">
import { ref, watchEffect } from "vue";
import { useGettext } from "vue3-gettext";

import { generateArchesURL } from "@/arches/utils/generate-arches-url.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";
import SideNavSection from "@/arches_lingo/components/sidenav/components/SideNavSection.vue";

import type { SideNavMenuItem } from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();

const props = defineProps<{
    item: SideNavMenuItem;
}>();

const userStore = useUserStore();

const profileItem: SideNavMenuItem = {
    key: "profile",
    label: $gettext("Profile"),
    icon: "pi pi-user",
    route: { name: routeNames.profile },
    showIconIfCollapsed: true,
};

const systemSettingsItem: SideNavMenuItem = {
    key: "system_settings",
    label: $gettext("System Settings"),
    icon: "pi pi-cog",
    url: generateArchesURL("arches:config"),
    showIconIfCollapsed: true,
};

const djangoAdminItem: SideNavMenuItem = {
    key: "django_admin",
    label: $gettext("Django Admin"),
    icon: "pi pi-wrench",
    url: "/admin/",
    showIconIfCollapsed: true,
};

const navSection = ref<SideNavMenuItem>(props.item);

watchEffect(() => {
    navSection.value.items = [
        profileItem,
        ...(userStore.canAccessAdminInterface
            ? [systemSettingsItem, djangoAdminItem]
            : []),
    ];
});
</script>

<template>
    <SideNavSection :item="navSection"></SideNavSection>
</template>
