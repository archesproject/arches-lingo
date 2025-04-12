<script setup lang="ts">
import { onMounted, ref } from "vue";

import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";

import HierarchicalPositionViewer from "@/arches_lingo/components/concept/HierarchicalPosition/components/HierarchicalPositionViewer.vue";
import HierarchicalPositionEditor from "@/arches_lingo/components/concept/HierarchicalPosition/components/HierarchicalPositionEditor.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";
import {
    fetchConceptResources,
    fetchLingoResourcePartial,
} from "@/arches_lingo/api.ts";
import type {
    ConceptClassificationStatus,
    DataComponentMode,
    SearchResultItem,
    SearchResultHierarchy,
} from "@/arches_lingo/types.ts";

const props = defineProps<{
    mode: DataComponentMode;
    sectionTitle: string;
    componentName: string;
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId: string | undefined;
    tileId?: string;
}>();

const isLoading = ref(true);
const fetchError = ref();
const concepts = ref<string[]>([props.resourceInstanceId!]); // Ensure we have a resource instance id for fetching
const hierarchicalData = ref<SearchResultHierarchy[]>();
const schemeId = ref<string>();
const tileData = ref<ConceptClassificationStatus[]>();

const shouldCreateNewTile = Boolean(props.mode === EDIT && !props.tileId);

onMounted(async () => {
    if (props.resourceInstanceId) {
        if (props.mode === VIEW || !shouldCreateNewTile) {
            const sectionValue = await getSectionValue();
            tileData.value = sectionValue.aliased_data[props.nodegroupAlias];
        }
        const parent_concepts =
            tileData.value?.map(
                (tile) =>
                    tile.aliased_data
                        .classification_status_ascribed_classification[0]
                        .resourceId,
            ) || [];
        // if (parent_concepts) {
        //     concepts.value = concepts.value.concat(parent_concepts);
        // }

        const currentPosition = await getHierarchicalData(concepts.value);
        const parentsPosition = await getHierarchicalData(parent_concepts);

        schemeId.value = currentPosition?.data[0].parents[0].id;
        hierarchicalData.value = parentsPosition?.data.map(
            (datum: SearchResultItem) => {
                const hierarchicalArray = datum.parents;
                hierarchicalArray.push(datum);
                hierarchicalArray.push(currentPosition.data[0]);
                return { searchResults: hierarchicalArray };
            },
        );

        if (hierarchicalData.value && tileData.value) {
            for (const datum of hierarchicalData.value) {
                datum.tileid = tileData.value.find(
                    (tile) =>
                        tile.aliased_data
                            .classification_status_ascribed_classification[0]
                            .resourceId === datum.searchResults[datum.searchResults.length - 2].id,
                )?.tileid;
            }
        }
    }
    isLoading.value = false;
});

async function getHierarchicalData(conceptIds: string[]) {
    try {
        if (conceptIds.length === 0) {
            return;
        }
        return await fetchConceptResources(
            "",
            conceptIds.length,
            1,
            undefined,
            undefined,
            conceptIds,
        );
    } catch (error) {
        fetchError.value = error;
    }
}

async function getSectionValue() {
    try {
        const sectionValue = await fetchLingoResourcePartial(
            props.graphSlug,
            props.resourceInstanceId as string,
            props.nodegroupAlias,
        );
        return sectionValue;
    } catch (error) {
        fetchError.value = error;
    }
}
</script>

<template>
    <ProgressSpinner
        v-if="isLoading"
        style="width: 100%"
    />
    <Message
        v-else-if="fetchError"
        severity="error"
        size="small"
    >
        {{ fetchError.message }}
    </Message>
    <template v-else>
        <HierarchicalPositionViewer
            v-if="mode === VIEW"
            :data="hierarchicalData"
            :section-title="props.sectionTitle"
            :component-name="props.componentName"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
            :resource-instance-id="props.resourceInstanceId"
            :scheme="schemeId"
        />
        <HierarchicalPositionEditor
            v-else-if="mode === EDIT"
            :tile-data="
                tileData?.find((tileDatum) => tileDatum.tileid === props.tileId)
            "
            :section-title="props.sectionTitle"
            :component-name="props.componentName"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
            :resource-instance-id="props.resourceInstanceId"
            :scheme="schemeId"
            :tile-id="props.tileId"
        />
    </template>
</template>
