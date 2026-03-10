<script setup lang="ts">
import { ref, useTemplateRef } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Skeleton from "primevue/skeleton";

import ResourceListEditor from "@/arches_lingo/components/generic/ResourceListEditor/ResourceListEditor.vue";
import ResourceNameCard from "@/arches_lingo/components/generic/ResourceNameCard/ResourceNameCard.vue";
import { useResourceNameEditor } from "@/arches_lingo/composables/useResourceNameEditor.ts";
import { fetchSources } from "@/arches_lingo/api.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

import type { ResourceSummary } from "@/arches_lingo/types";

const GRAPH_SLUG = "textual_work";

const { $gettext } = useGettext();
const { isEditor } = useUserStore();

const genericCardRef = useTemplateRef("genericCardRef");
const hasUnsavedChanges = ref(false);
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

async function onSelectResource(resource: ResourceSummary) {
    hasUnsavedChanges.value = false;
    await selectResource(resource);
}

function onCreateNew() {
    hasUnsavedChanges.value = false;
    clearSelection();
}

function onWidgetDirtyStatesChange(states: Record<string, boolean>) {
    hasUnsavedChanges.value = Object.values(states).some(Boolean);
}

function onCancel() {
    hasUnsavedChanges.value = false;
    editorKey.value++;
}

function onSave() {
    hasUnsavedChanges.value = false;
    refreshTrigger.value++;
}
</script>

<template>
    <ResourceListEditor
        :page-title="$gettext('Sources')"
        :fetch-resources="fetchSources"
        :refresh-trigger="refreshTrigger"
        :editor-enabled="isEditor"
        @select-resource="onSelectResource"
    >
        <template #list-actions="{ openBlankEditor }">
            <Button
                v-if="isEditor"
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
            <ResourceNameCard
                v-else
                ref="genericCardRef"
                :key="editorKey"
                :graph-slug="GRAPH_SLUG"
                :nodegroup-alias="NAME_NODEGROUP_ALIAS"
                :resource-instance-id="
                    isCreatingNew ? undefined : selectedResourceInstanceId
                "
                :tile-id="isCreatingNew ? undefined : selectedTileId"
                @update:widget-dirty-states="onWidgetDirtyStatesChange"
                @save="onSave"
            />
        </template>

        <template #editor-footer>
            <Button
                :label="$gettext('Save')"
                severity="success"
                size="small"
                icon="pi pi-check"
                :disabled="!hasUnsavedChanges"
                @click="genericCardRef?.save()"
            />
            <Button
                :label="$gettext('Cancel')"
                severity="warn"
                size="small"
                icon="pi pi-undo"
                :disabled="!hasUnsavedChanges"
                @click="onCancel"
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
