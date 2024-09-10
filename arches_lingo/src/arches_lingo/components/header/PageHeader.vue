<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Menubar from "primevue/menubar";

import { routeNames } from "@/arches_lingo/routes.ts";
import UserInteraction from "@/arches_lingo/components/user/UserInteraction.vue";

const { $gettext } = useGettext();

const items = ref([
    {
        label: $gettext("Search"),
        icon: "fa fa-search",
        name: routeNames.search,
    },
    {
        label: $gettext("Advanced Search"),
        icon: "fa fa-file",
        name: routeNames.advancedSearch,
    },
]);
</script>

<template>
    <Menubar :model="items">
        <template #start>
            <RouterLink
                :to="{ name: routeNames.root }"
                style="text-decoration: none; color: inherit"
            >
                <h1>{{ $gettext("Arches Lingo") }}</h1>
            </RouterLink>
        </template>
        <template #item="{ item }">
            <RouterLink
                :to="{ name: item.name }"
                class="p-button p-component p-button-primary"
                style="text-decoration: none"
            >
                <i
                    :class="item.icon"
                    aria-hidden="true"
                ></i>
                <span style="font-weight: var(--p-button-label-font-weight)">{{
                    item.label
                }}</span>
            </RouterLink>
        </template>
        <template #end>
            <UserInteraction />
        </template>
    </Menubar>
</template>

<style scoped>
:deep(.p-menubar-start) {
    gap: var(--p-menubar-gap);
}

@media screen and (max-width: 960px) {
    :deep(.p-menubar-button) {
        display: none !important;
    }
}
</style>
