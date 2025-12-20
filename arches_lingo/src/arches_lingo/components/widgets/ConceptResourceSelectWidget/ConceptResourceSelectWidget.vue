<script setup lang="ts">
import { watchEffect, ref } from "vue";

import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";

import ConceptResourceSelectWidgetEditor from "@/arches_lingo/components/widgets/ConceptResourceSelectWidget/components/ConceptResourceSelectWidgetEditor.vue";
import ConceptResourceSelectWidgetViewer from "@/arches_lingo/components/widgets/ConceptResourceSelectWidget/components/ConceptResourceSelectWidgetViewer.vue";

import { fetchCardXNodeXWidgetData } from "@/arches_component_lab/generics/GenericWidget/api.ts";
import { fetchConceptResources } from "@/arches_lingo/api.ts";
import { EDIT, VIEW } from "@/arches_component_lab/widgets/constants.ts";

import type { CardXNodeXWidgetData } from "@/arches_component_lab/types.ts";
import type { WidgetMode } from "@/arches_component_lab/widgets/types.ts";
import type { ResourceInstanceListValue } from "@/arches_component_lab/datatypes/resource-instance-list/types";

const props = withDefaults(
    defineProps<{
        mode: WidgetMode;
        value: ResourceInstanceListValue | null | undefined;
        nodeAlias: string;
        graphSlug: string;
        scheme?: string;
        exclude?: boolean | false;
        showLabel?: boolean;
        schemeSelectable?: boolean | false;
    }>(),
    {
        scheme: "",
        showLabel: true,
    },
);

const isLoading = ref(true);
const cardXNodeXWidgetData = ref<CardXNodeXWidgetData>();
const configurationError = ref();
const conceptIds = props.value?.details.map((resource: { display_value: string; resource_id: string }) => resource.resource_id) as string[] | undefined;
const searchResult = ref();

watchEffect(async () => {
    isLoading.value = true;
    try {
        if (conceptIds) {
            searchResult.value = await getConceptHierarchy(conceptIds);
        }
        cardXNodeXWidgetData.value = await fetchCardXNodeXWidgetData(
            props.graphSlug,
            props.nodeAlias,
        );
        console.log("cardXNodeXWidgetData", cardXNodeXWidgetData.value);
    } catch (error) {
        configurationError.value = error;
    } finally {
        isLoading.value = false;
    }
});

async function getConceptHierarchy(conceptIds: string[]) {
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
    <ProgressSpinner
        v-if="isLoading"
        style="width: 2em; height: 2em"
    />

    <template v-else>
        <label v-if="props.showLabel">
            <span>{{ cardXNodeXWidgetData }}</span>
            <!-- <span>{{ cardXNodeXWidgetData!.label }}</span>
            <span v-if="cardXNodeXWidgetData!.node.isrequired && props.mode === EDIT">*</span> -->
        </label>

        <div v-if="mode === EDIT">
            <ConceptResourceSelectWidgetEditor
                :value="searchResult"
                :node-alias="props.nodeAlias"
                :graph-slug="props.graphSlug"
                :scheme="props.scheme"
                :exclude="props.exclude"
                :scheme-selectable="props.schemeSelectable"
            />
        </div>
        <div v-if="mode === VIEW">
            <ConceptResourceSelectWidgetViewer :value="searchResult" />
        </div>
        <Message
            v-if="configurationError"
            severity="error"
            size="small"
        >
            {{ configurationError.message }}
        </Message>
    </template>
</template>
