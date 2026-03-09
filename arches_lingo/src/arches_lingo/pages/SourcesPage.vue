<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Skeleton from "primevue/skeleton";

import GenericCard from "@/arches_component_lab/generics/GenericCard/GenericCard.vue";
import { EDIT } from "@/arches_component_lab/widgets/constants.ts";

import ResourceListEditor from "@/arches_lingo/components/generic/ResourceListEditor/ResourceListEditor.vue";
import { fetchLingoResourcePartial, fetchSources } from "@/arches_lingo/api.ts";

import type { ResourceSummary } from "@/arches_lingo/types";

const GRAPH_SLUG = "textual_work";
const NODEGROUP_ALIAS = "name";

const { $gettext } = useGettext();

const listEditorRef = ref<InstanceType<typeof ResourceListEditor>>();
const selectedResourceInstanceId = ref<string | null>(null);
const selectedTileId = ref<string | null>(null);
const isLoadingTile = ref(false);
const editorKey = ref(0);

async function onSelectResource(resource: ResourceSummary) {
    selectedResourceInstanceId.value = resource.resourceinstanceid;
    isLoadingTile.value = true;

    try {
        const partialData = await fetchLingoResourcePartial(
            resource.graph_slug,
            resource.resourceinstanceid,
            NODEGROUP_ALIAS,
        );
        const nameTiles = partialData?.aliased_data?.name;
        selectedTileId.value =
            Array.isArray(nameTiles) && nameTiles.length > 0
                ? nameTiles[0].tileid
                : null;
    } catch {
        selectedTileId.value = null;
    }

    editorKey.value++;
    isLoadingTile.value = false;
}

function onCreateNew() {
    selectedResourceInstanceId.value = null;
    selectedTileId.value = null;
    editorKey.value++;
    listEditorRef.value?.openBlankEditor();
}

function onSave() {
    listEditorRef.value?.refreshList();
}
</script>

<template>
    <ResourceListEditor
        ref="listEditorRef"
        :page-title="$gettext('Sources')"
        :fetch-resources="fetchSources"
        @select-resource="onSelectResource"
    >
        <template #list-actions>
            <Button
                :label="$gettext('Add Source')"
                icon="pi pi-plus"
                size="small"
                @click="onCreateNew"
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
                :nodegroup-alias="NODEGROUP_ALIAS"
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
