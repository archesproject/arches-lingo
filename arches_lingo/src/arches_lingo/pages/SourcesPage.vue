<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Skeleton from "primevue/skeleton";

import GenericCard from "@/arches_component_lab/generics/GenericCard/GenericCard.vue";
import { EDIT } from "@/arches_component_lab/widgets/constants.ts";

import ResourceListEditor from "@/arches_lingo/components/generic/ResourceListEditor/ResourceListEditor.vue";
import { useResourceNameEditor } from "@/arches_lingo/composables/useResourceNameEditor.ts";
import { fetchSources } from "@/arches_lingo/api.ts";

const GRAPH_SLUG = "textual_work";

const { $gettext } = useGettext();

const refreshTrigger = ref(0);
const {
    selectedResourceInstanceId,
    selectedTileId,
    isLoadingTile,
    editorKey,
    selectResource,
    clearSelection,
    NAME_NODEGROUP_ALIAS,
} = useResourceNameEditor();

function onCreateNew() {
    clearSelection();
}

function onSave() {
    refreshTrigger.value++;
}
</script>

<template>
    <ResourceListEditor
        :page-title="$gettext('Sources')"
        :fetch-resources="fetchSources"
        :refresh-trigger="refreshTrigger"
        @select-resource="selectResource"
    >
        <template #list-actions="{ openBlankEditor }">
            <Button
                :label="$gettext('Add Source')"
                icon="pi pi-plus-circle"
                class="add-button"
                @click="
                    () => {
                        onCreateNew();
                        openBlankEditor();
                    }
                "
            />
        </template>

        <template #editor="{ isCreatingNew }">
            <Skeleton
                v-if="isLoadingTile"
                height="10rem"
            />
            <GenericCard
                v-else
                :key="editorKey"
                :mode="EDIT"
                :graph-slug="GRAPH_SLUG"
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
</style>
