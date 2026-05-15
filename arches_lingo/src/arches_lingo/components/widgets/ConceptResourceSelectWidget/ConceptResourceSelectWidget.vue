<script setup lang="ts">
import { watchEffect, ref } from "vue";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import GenericWidgetLabel from "@/arches_component_lab/generics/GenericWidget/components/GenericWidgetLabel.vue";
import GenericFormField from "@/arches_component_lab/generics/GenericWidget/components/GenericFormField.vue";
import ConceptResourceSelectWidgetEditor from "@/arches_lingo/components/widgets/ConceptResourceSelectWidget/components/ConceptResourceSelectWidgetEditor.vue";
import ConceptResourceSelectWidgetViewer from "@/arches_lingo/components/widgets/ConceptResourceSelectWidget/components/ConceptResourceSelectWidgetViewer.vue";

import { fetchCardXNodeXWidgetData } from "@/arches_component_lab/generics/GenericWidget/api.ts";
import { fetchConceptResources } from "@/arches_lingo/api.ts";
import { useWidgetReadyTracker } from "@/arches_lingo/composables/useWidgetReadyTracker.ts";
import { EDIT, VIEW } from "@/arches_component_lab/widgets/constants.ts";

import type { CardXNodeXWidgetData } from "@/arches_component_lab/types.ts";
import type { WidgetMode } from "@/arches_component_lab/widgets/types.ts";
import type { ResourceInstanceReference } from "@/arches_component_lab/datatypes/resource-instance-list/types";

const {
    graphSlug,
    mode,
    nodeAlias,
    resourceInstanceId,
    value,
    shouldShowLabel = true,
    isDirty = false,
    scheme = "",
    schemeSelectable = false,
} = defineProps<{
    graphSlug: string;
    isDirty?: boolean;
    mode: WidgetMode;
    nodeAlias: string;
    resourceInstanceId?: string;
    value: ResourceInstanceReference[] | null | undefined;
    shouldShowLabel?: boolean;
    scheme?: string;
    schemeSelectable?: boolean | false;
}>();

const emit = defineEmits([
    "update:isDirty",
    "update:isFocused",
    "update:value",
    "update:isLoading",
]);

const isLoading = ref(true);
const cardXNodeXWidgetData = ref<CardXNodeXWidgetData>();
const configurationError = ref();

const widgetReadyTracker = useWidgetReadyTracker();
if (widgetReadyTracker) {
    widgetReadyTracker.register();
}

const conceptIds = value?.map((ref) => ref.resourceId);
const searchResult = ref();

watchEffect(async () => {
    if (cardXNodeXWidgetData.value) {
        return;
    }

    isLoading.value = true;
    try {
        if (conceptIds) {
            searchResult.value = await getConceptHierarchy(conceptIds);
        }
        cardXNodeXWidgetData.value = await fetchCardXNodeXWidgetData(
            graphSlug,
            nodeAlias,
        );
    } catch (error) {
        configurationError.value = error;
    } finally {
        isLoading.value = false;
        widgetReadyTracker?.reportReady();
    }
});

async function getConceptHierarchy(conceptIds: string[]) {
    if (conceptIds.length === 0) {
        return;
    }
    const parsedResponse = await fetchConceptResources(
        "",
        conceptIds.length,
        1,
        undefined,
        undefined,
        conceptIds,
    );
    return parsedResponse.data;
}
</script>

<template>
    <Skeleton
        v-if="isLoading"
        style="height: 2rem"
    />
    <Message
        v-else-if="configurationError"
        severity="error"
        size="small"
    >
        {{ configurationError.message }}
    </Message>
    <template v-else-if="cardXNodeXWidgetData">
        <GenericWidgetLabel
            v-if="shouldShowLabel"
            :mode="mode"
            :card-x-node-x-widget-data="cardXNodeXWidgetData"
        />
        <GenericFormField
            v-if="mode === EDIT"
            v-slot="{ onUpdateValue }"
            :value="value"
            :is-dirty="isDirty"
            :node-alias="nodeAlias"
            @update:is-dirty="emit('update:isDirty', $event)"
            @update:value="emit('update:value', $event)"
        >
            <ConceptResourceSelectWidgetEditor
                :value="searchResult"
                :node-alias="nodeAlias"
                :resource-instance-id="resourceInstanceId"
                :graph-slug="graphSlug"
                :scheme="scheme"
                :scheme-selectable="schemeSelectable"
                @update:value="onUpdateValue($event)"
                @update:is-editor-mounted="emit('update:isLoading', $event)"
            />
        </GenericFormField>
        <ConceptResourceSelectWidgetViewer
            v-else-if="mode === VIEW"
            :value="searchResult"
        />
    </template>
</template>
