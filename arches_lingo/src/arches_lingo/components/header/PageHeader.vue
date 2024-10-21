<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Menubar from "primevue/menubar";

import { routeNames } from "@/arches_lingo/routes.ts";
import UserInteraction from "@/arches_lingo/components/user/UserInteraction.vue";
import SearchDialogue from "@/arches_lingo/components/header/SearchDialogue.vue";

const { $gettext } = useGettext();

const { header } = defineProps<{ header: string }>();

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
        class="page-header"
        :model="items"
    >
        <template #start>
            <RouterLink
                :to="{ name: routeNames.root }"
                style="text-decoration: none; color: inherit"
            >
                <h2>{{ header }}</h2>
            </RouterLink>
            <SearchDialogue />
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
                <span>{{ item.label }}</span>
            </RouterLink>
        </template>
        <template #end>
            <UserInteraction />
        </template>
    </Menubar>
</template>

<style scoped>
.page-header {
    border-radius: 0;
}

@media screen and (max-width: 960px) {
    :deep(.p-menubar-button) {
        display: none !important;
    }
}
</style>
