<!-- <script setup lang="ts">
import { onMounted, ref } from "vue";

import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";

import ConceptResourceSelectWidgetEditor from "@/arches_lingo/components/widgets/ConceptResourceSelectWidget/components/ConceptResourceSelectWidgetEditor.vue";
import ConceptResourceSelectWidgetViewer from "@/arches_lingo/components/widgets/ConceptResourceSelectWidget/components/ConceptResourceSelectWidgetViewer.vue";

import {
    fetchWidgetData,
    fetchNodeData,
} from "@/arches_component_lab/widgets/api.ts";
import { fetchConceptResources } from "@/arches_lingo/api.ts";
import { EDIT, VIEW } from "@/arches_component_lab/widgets/constants.ts";

import type {
    ResourceInstanceReference,
    WidgetMode,
} from "@/arches_component_lab/widgets/types.ts";

const props = withDefaults(
    defineProps<{
        mode: WidgetMode;
        initialValue: ResourceInstanceReference | null | undefined;
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
const nodeData = ref();
const widgetData = ref();
const configurationError = ref();
const conceptIds = [props.initialValue?.resource_id] as string[] | undefined;
const searchResult = ref();

onMounted(async () => {
    try {
        if (conceptIds) {
            await getConceptHierarchy(conceptIds);
        }
        widgetData.value = await fetchWidgetData(
            props.graphSlug,
            props.nodeAlias,
        );
        nodeData.value = await fetchNodeData(props.graphSlug, props.nodeAlias);
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
    searchResult.value = parsedResponse.data;
}
</script>

<template>
    <ProgressSpinner
        v-if="isLoading"
        style="width: 2em; height: 2em"
    />

    <template v-else>
        <label v-if="props.showLabel">
            <span>{{ widgetData.label }}</span>
            <span v-if="nodeData.isrequired && props.mode === EDIT">*</span>
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
</template> -->
