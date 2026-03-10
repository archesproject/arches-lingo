<script setup lang="ts">
import { ref, useTemplateRef, watchEffect } from "vue";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import GenericCardEditor from "@/arches_component_lab/generics/GenericCard/components/GenericCardEditor.vue";
import {
    fetchTileData,
    fetchCardXNodeXWidgetDataFromNodeGroup,
} from "@/arches_component_lab/generics/GenericCard/api.ts";

import { EDIT } from "@/arches_component_lab/widgets/constants.ts";

import type {
    AliasedTileData,
    CardXNodeXWidgetData,
} from "@/arches_component_lab/types.ts";

const { graphSlug, nodegroupAlias, resourceInstanceId, tileId } = defineProps<{
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId?: string | null;
    tileId?: string | null;
}>();

const emit = defineEmits([
    "update:tileData",
    "update:widgetDirtyStates",
    "update:widgetFocusStates",
    "save",
    "reset",
]);

const isLoading = ref(true);
const configurationError = ref<Error>();
const cardXNodeXWidgetData = ref<CardXNodeXWidgetData[]>([]);
const aliasedTileData = ref<AliasedTileData>();

const cardEditorRef = useTemplateRef("cardEditorRef");

watchEffect(async () => {
    isLoading.value = true;

    try {
        const cardXNodeXWidgetDataPromise =
            fetchCardXNodeXWidgetDataFromNodeGroup(graphSlug, nodegroupAlias);

        aliasedTileData.value = await fetchTileData(
            graphSlug,
            nodegroupAlias,
            tileId,
        );
        if (!tileId && resourceInstanceId) {
            aliasedTileData.value.resourceinstance = resourceInstanceId;
        }

        cardXNodeXWidgetData.value = await cardXNodeXWidgetDataPromise;
    } catch (error) {
        configurationError.value = error as Error;
    } finally {
        isLoading.value = false;
    }
});

defineExpose({
    save() {
        cardEditorRef.value?.save();
    },
});
</script>

<template>
    <Skeleton
        v-if="isLoading"
        style="height: 10rem"
    />
    <Message
        v-else-if="configurationError"
        severity="error"
    >
        {{ configurationError.message }}
    </Message>
    <GenericCardEditor
        v-else
        ref="cardEditorRef"
        v-model:tile-data="aliasedTileData"
        :card-x-node-x-widget-data="cardXNodeXWidgetData"
        :graph-slug="graphSlug"
        :mode="EDIT"
        :nodegroup-alias="nodegroupAlias"
        :resource-instance-id="resourceInstanceId"
        :should-show-form-buttons="false"
        @save="emit('save', $event)"
        @reset="emit('reset', $event)"
        @update:tile-data="emit('update:tileData', $event)"
        @update:widget-dirty-states="emit('update:widgetDirtyStates', $event)"
        @update:widget-focus-states="emit('update:widgetFocusStates', $event)"
    />
</template>
