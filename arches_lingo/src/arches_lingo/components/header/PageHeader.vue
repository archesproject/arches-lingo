<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Menubar from "primevue/menubar";

import { routeNames } from "@/arches_lingo/routes.ts";
import DarkModeToggle from "@/arches_lingo/components/header/DarkModeToggle.vue";
import UserInteraction from "@/arches_lingo/components/user/UserInteraction.vue";
import SearchDialog from "@/arches_lingo/components/header/SearchDialog.vue";

const { $gettext } = useGettext();

const items = ref([
    {
        label: $gettext("Advanced Search"),
        icon: "fa fa-file",
        name: routeNames.advancedSearch,
    },
]);
</script>

<template>
    <Menubar
        :model="items"
        style="border-radius: 0"
    >
        <template #start>
            <RouterLink
                :to="{ name: routeNames.root }"
                style="text-decoration: none; color: inherit"
            >
                <h1>{{ $gettext("Arches Lingo") }}</h1>
            </RouterLink>
            <SearchDialog />
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
                />
                <span style="font-weight: var(--p-button-label-font-weight)">
                    {{ item.label }}
                </span>
            </RouterLink>
        </template>
        <template #end>
            <div style="display: flex; align-items: center; gap: 1rem">
                <DarkModeToggle />
                <UserInteraction />
            </div>
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
