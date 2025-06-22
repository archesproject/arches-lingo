<script setup lang="ts">
import type { Component } from "vue";
import type { MenuItem } from "primevue/menuitem";

import SideNavSection from "@/arches_lingo/components/sidenav/SideNavSection.vue";

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
</script>

<template>
    <SideNavSection :item="props.item"></SideNavSection>
</template>
