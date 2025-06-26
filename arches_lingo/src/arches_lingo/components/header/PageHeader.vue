<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Menubar from "primevue/menubar";
import Button from "primevue/button";
import { routeNames } from "@/arches_lingo/routes.ts";
import HierarchyOverlay from "@/arches_lingo/components/tree/HierarchyOverlay.vue";
import UserInteraction from "@/arches_lingo/components/user/UserInteraction/UserInteraction.vue";
import SearchDialog from "@/arches_lingo/components/header/SearchDialog.vue";

import { generateArchesURL } from "@/arches/utils/generate-arches-url.ts";

const { $gettext } = useGettext();
const showHierarchy = ref();

const items = ref([]);

function activateHierarchyOverlay() {
    showHierarchy.value = true;
}
</script>

<template>
    <Menubar
        :model="items"
        style="border-radius: 0; border-inline-start: 0; border-inline-end: 0"
    >
        <template #start>
            <RouterLink
                :to="{ name: routeNames.root }"
                style="text-decoration: none; color: inherit"
            >
                <div class="lingo-branding">
                    <img
                        :src="
                            generateArchesURL('static_url') +
                            'img/arches_logo_light.png'
                        "
                        alt="Arches Logo"
                        style="height: 1.5rem; width: auto"
                    />
                    <h1 class="lingo-title">{{ $gettext("Lingo") }}</h1>
                </div>
            </RouterLink>
            <Button
                icon="pi pi-globe"
                class="toggle-hierarchy"
                :label="$gettext('Explore...')"
                @click="activateHierarchyOverlay"
            />
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
                ></i>
                <span style="font-weight: var(--p-button-label-font-weight)">
                    {{ item.label }}
                </span>
            </RouterLink>
        </template>
        <template #end>
            <div style="display: flex; align-items: center; gap: 1rem">
                <!-- <DarkModeToggle /> -->
                <UserInteraction />
            </div>
        </template>
    </Menubar>
    <HierarchyOverlay v-model:show-hierarchy="showHierarchy" />
</template>

<style scoped>
:deep(.p-menubar-start) {
    gap: var(--p-menubar-gap);
}

.p-menubar {
    height: 3.125rem;
    border-radius: 0;
    border: none;
}

.lingo-branding {
    display: flex;
    align-items: center;
    margin-bottom: 0.15rem;
}

.lingo-title {
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-large);
    margin: 0rem;
    margin-inline-start: 0.5rem;
}

@media screen and (max-width: 960px) {
    :deep(.p-menubar-button) {
        display: none !important;
    }
}
</style>
