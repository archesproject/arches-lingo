<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";
import { generateArchesURL } from "@/arches/utils/generate-arches-url.ts";

import SideNavSection from "@/arches_lingo/components/sidenav/components/SideNavSection.vue";

import type { SideNavMenuItem } from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();

const props = defineProps<{
    item: SideNavMenuItem;
}>();

const children = <SideNavMenuItem[]>[
    {
        key: "controlled_lists",
        label: $gettext("Controlled List Manager"),
        icon: "pi pi-list",
        url: generateArchesURL("arches:plugins", {
            pluginid: "controlled-list-manager",
        }),
        showIconIfCollapsed: true,
    },
    {
        key: "system_settings",
        label: $gettext("System Settings"),
        icon: "pi pi-cog",
        url: generateArchesURL("arches:config"),
        showIconIfCollapsed: true,
    },
    {
        key: "django_admin",
        label: $gettext("Administration"),
        icon: "pi pi-shield",
        url: generateArchesURL("admin", { url: "" }),
        showIconIfCollapsed: true,
    },
];

const navSection = ref<SideNavMenuItem>(props.item);
navSection.value.items = children;
</script>

<template>
    <SideNavSection :item="navSection"></SideNavSection>
</template>
