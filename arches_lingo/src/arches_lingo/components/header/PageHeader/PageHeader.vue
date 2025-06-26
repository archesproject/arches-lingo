<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Menubar from "primevue/menubar";
import Button from "primevue/button";
import HierarchyOverlay from "@/arches_lingo/components/tree/HierarchyOverlay.vue";
import UserInteraction from "@/arches_lingo/components/user/UserInteraction/UserInteraction.vue";
import SearchDialog from "@/arches_lingo/components/header/PageHeader/components/SearchDialog.vue";

import ArchesLingoBadge from "@/arches_lingo/components/header/PageHeader/components/ArchesLingoBadge.vue";

const { $gettext } = useGettext();

const props = defineProps<{
    isNavExpanded: boolean;
}>();

const showHierarchy = ref();
const items = ref([]);

function activateHierarchyOverlay() {
    showHierarchy.value = true;
}
</script>

<template>
    <Menubar
        :model="items"
        style="
            border-radius: 0;
            border-inline-start: 0;
            border-inline-end: 0;
            padding-inline-start: 1rem;
        "
    >
        <template #start>
            <ArchesLingoBadge v-if="!props.isNavExpanded" />

            <Button
                icon="pi pi-globe"
                variant="text"
                class="explore-button"
                :label="$gettext('Explore')"
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
.explore-button {
    color: var(--p-menubar-text-color) !important;
}

.explore-button:hover {
    background: var(--p-button-primary-hover-background) !important;
}

:deep(.p-menubar-start) {
    gap: var(--p-menubar-gap);
}

.p-menubar {
    height: 3.125rem;
    border-radius: 0;
    border: none;
}

@media screen and (max-width: 960px) {
    :deep(.p-menubar-button) {
        display: none !important;
    }
}
</style>
