<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Select from "primevue/select";
import Skeleton from "primevue/skeleton";

import GenericCard from "@/arches_component_lab/generics/GenericCard/GenericCard.vue";
import { EDIT } from "@/arches_component_lab/widgets/constants.ts";

import ResourceListEditor from "@/arches_lingo/components/generic/ResourceListEditor/ResourceListEditor.vue";
import { useResourceNameEditor } from "@/arches_lingo/composables/useResourceNameEditor.ts";
import { fetchContributors } from "@/arches_lingo/api.ts";

import type { ResourceSummary } from "@/arches_lingo/types";

interface GraphTypeOption {
    label: string;
    value: string;
}

const { $gettext } = useGettext();

const graphTypeOptions: GraphTypeOption[] = [
    { label: $gettext("Person"), value: "person_system" },
    { label: $gettext("Group"), value: "group" },
];

const refreshTrigger = ref(0);
const selectedGraphSlug = ref<string>("person_system");
const newGraphSlug = ref<GraphTypeOption>(graphTypeOptions[0]);
const {
    selectedResourceInstanceId,
    selectedTileId,
    isLoadingTile,
    editorKey,
    selectResource,
    clearSelection,
    NAME_NODEGROUP_ALIAS,
} = useResourceNameEditor();

async function onSelectResource(resource: ResourceSummary) {
    selectedGraphSlug.value = resource.graph_slug;
    await selectResource(resource);
}

function onCreateNew(openBlankEditor: () => void) {
    selectedGraphSlug.value = newGraphSlug.value.value;
    clearSelection();
    openBlankEditor();
}

function onNewGraphTypeChange() {
    selectedGraphSlug.value = newGraphSlug.value.value;
    editorKey.value++;
}

function onSave() {
    refreshTrigger.value++;
}
</script>

<template>
    <ResourceListEditor
        :page-title="$gettext('Contributors')"
        :fetch-resources="fetchContributors"
        :refresh-trigger="refreshTrigger"
        :show-graph-type="true"
        @select-resource="onSelectResource"
    >
        <template #list-actions="{ openBlankEditor }">
            <Button
                :label="$gettext('Add Contributor')"
                icon="pi pi-plus-circle"
                class="add-button"
                @click="() => onCreateNew(openBlankEditor)"
            />
        </template>

        <template #editor="{ isCreatingNew }">
            <div
                v-if="isCreatingNew"
                class="new-contributor-type-selector"
            >
                <label class="type-selector-label">
                    {{ $gettext("Contributor Type") }}
                </label>
                <Select
                    v-model="newGraphSlug"
                    :options="graphTypeOptions"
                    option-label="label"
                    :placeholder="$gettext('Select type')"
                    class="type-selector"
                    @change="onNewGraphTypeChange"
                />
            </div>

            <Skeleton
                v-if="isLoadingTile"
                height="10rem"
            />
            <GenericCard
                v-else
                :key="editorKey"
                :mode="EDIT"
                :graph-slug="selectedGraphSlug"
                :nodegroup-alias="NAME_NODEGROUP_ALIAS"
                :resource-instance-id="
                    isCreatingNew ? undefined : selectedResourceInstanceId
                "
                :tile-id="isCreatingNew ? undefined : selectedTileId"
                :should-show-form-buttons="true"
                @save="onSave"
            />
        </template>
    </ResourceListEditor>
</template>

<style scoped>
.add-button {
    font-size: var(--p-lingo-font-size-xsmall);
    font-weight: var(--p-lingo-font-weight-normal);
    background: var(--p-header-button-background);
    color: var(--p-header-button-color);
    border-color: var(--p-header-button-border);
    border-radius: 0.125rem;
}

.add-button:hover {
    background: var(--p-highlight-background);
    color: var(--p-highlight-color);
}

.new-contributor-type-selector {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 1rem;
}

.type-selector-label {
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-header-item-label);
}

.type-selector {
    width: 100%;
    border-radius: 0.125rem;
}
</style>
