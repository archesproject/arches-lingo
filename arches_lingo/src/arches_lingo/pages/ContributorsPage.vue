<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Select from "primevue/select";
import Skeleton from "primevue/skeleton";

import GenericCard from "@/arches_component_lab/generics/GenericCard/GenericCard.vue";
import { EDIT } from "@/arches_component_lab/widgets/constants.ts";

import ResourceListEditor from "@/arches_lingo/components/generic/ResourceListEditor/ResourceListEditor.vue";
import {
    fetchContributors,
    fetchLingoResourcePartial,
} from "@/arches_lingo/api.ts";

import type { ResourceSummary } from "@/arches_lingo/types";

const NODEGROUP_ALIAS = "name";

interface GraphTypeOption {
    label: string;
    value: string;
}

const { $gettext } = useGettext();

const graphTypeOptions: GraphTypeOption[] = [
    { label: $gettext("Person"), value: "person_system" },
    { label: $gettext("Group"), value: "group" },
];

const listEditorRef = ref<InstanceType<typeof ResourceListEditor>>();
const selectedResourceInstanceId = ref<string | null>(null);
const selectedTileId = ref<string | null>(null);
const selectedGraphSlug = ref<string>("person_system");
const newGraphSlug = ref<GraphTypeOption>(graphTypeOptions[0]);
const isLoadingTile = ref(false);
const editorKey = ref(0);

async function onSelectResource(resource: ResourceSummary) {
    selectedResourceInstanceId.value = resource.resourceinstanceid;
    selectedGraphSlug.value = resource.graph_slug;
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
    selectedGraphSlug.value = newGraphSlug.value.value;
    editorKey.value++;
    listEditorRef.value?.openBlankEditor();
}

function onNewGraphTypeChange() {
    selectedGraphSlug.value = newGraphSlug.value.value;
    editorKey.value++;
}

function onSave() {
    listEditorRef.value?.refreshList();
}
</script>

<template>
    <ResourceListEditor
        ref="listEditorRef"
        :page-title="$gettext('Contributors')"
        :fetch-resources="fetchContributors"
        :show-graph-type="true"
        @select-resource="onSelectResource"
    >
        <template #list-actions>
            <Button
                :label="$gettext('Add Contributor')"
                icon="pi pi-plus"
                size="small"
                @click="onCreateNew"
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

<style scoped>
.new-contributor-type-selector {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 1rem;
}

.type-selector-label {
    font-size: var(--p-lingo-font-size-small, 0.875rem);
    font-weight: var(--p-lingo-font-weight-normal, 600);
    color: var(--p-neutral-500);
}

.type-selector {
    width: 100%;
}
</style>
