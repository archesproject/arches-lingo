<script setup lang="ts">
import { inject, reactive, ref, useTemplateRef, watch, watchEffect } from "vue";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import GenericCardEditor from "@/arches_component_lab/generics/GenericCard/components/GenericCardEditor.vue";
import {
    fetchTileData,
    fetchCardXNodeXWidgetDataFromNodeGroup,
} from "@/arches_component_lab/generics/GenericCard/api.ts";

import { EDIT } from "@/arches_component_lab/widgets/constants.ts";

import type { Ref } from "vue";
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

const emit = defineEmits(["save"]);

const componentEditorFormRef = inject<Ref<unknown>>("componentEditorFormRef");

const isLoading = ref(true);
const configurationError = ref<Error>();
const cardXNodeXWidgetData = ref<CardXNodeXWidgetData[]>([]);
const aliasedTileData = ref<AliasedTileData>();
const widgetDirtyStates = ref<Record<string, boolean>>({});

const cardEditorRef = useTemplateRef("cardEditorRef");

const formFacade = reactive({
    states: {} as Record<string, { dirty: boolean }>,
    submit() {
        cardEditorRef.value?.save();
    },
});

watch(
    widgetDirtyStates,
    (newStates) => {
        formFacade.states = Object.fromEntries(
            Object.entries(newStates).map(([key, dirty]) => [key, { dirty }]),
        );
    },
    { deep: true },
);

watch(
    () => isLoading.value,
    (loading) => {
        if (!loading && componentEditorFormRef) {
            componentEditorFormRef.value = formFacade;
        }
    },
);

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
        @update:widget-dirty-states="widgetDirtyStates = $event"
    />
</template>
