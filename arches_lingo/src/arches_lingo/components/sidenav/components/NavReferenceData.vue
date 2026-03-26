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

const navSection = ref<SideNavMenuItem>(props.item);

watchEffect(() => {
    const baseChildren: SideNavMenuItem[] = [
        {
            key: "contributors",
            label: $gettext("Contributors"),
            icon: "pi pi-user-edit",
            route: { name: routeNames.contributors },
            showIconIfCollapsed: true,
        },
        {
            key: "sources",
            label: $gettext("Sources"),
            icon: "pi pi-bookmark-fill",
            route: { name: routeNames.sources },
            showIconIfCollapsed: true,
        },
    ];

    const controlledListManagerItem: SideNavMenuItem = {
        key: "controlled_lists",
        label: $gettext("Controlled List Manager"),
        icon: "pi pi-list",
        url: generateArchesURL("arches:plugins", {
            slug: "controlled-list-manager",
        }),
        showIconIfCollapsed: true,
    };

    if (userStore.isStaff) {
        navSection.value.items = [...baseChildren, controlledListManagerItem];
    } else {
        navSection.value.items = [...baseChildren];
    }
});
</script>

<template>
    <SideNavSection :item="navSection"></SideNavSection>
</template>
