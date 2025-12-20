<script setup lang="ts">
import { onMounted, ref } from "vue";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import HierarchicalPositionViewer from "@/arches_lingo/components/concept/HierarchicalPosition/components/HierarchicalPositionViewer.vue";
import HierarchicalPositionEditor from "@/arches_lingo/components/concept/HierarchicalPosition/components/HierarchicalPositionEditor.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

import { fetchTileData } from "@/arches_component_lab/generics/GenericCard/api.ts";
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
const hierarchicalData = ref<SearchResultHierarchy[]>([]);
const schemeId = ref<string>();
const tileData = ref<ConceptClassificationStatus[]>();
const topConceptOfTileId = ref<string>();

const shouldCreateNewTile = Boolean(props.mode === EDIT && !props.tileId);

onMounted(async () => {
    if (
        props.resourceInstanceId &&
        (props.mode === VIEW || !shouldCreateNewTile)
    ) {
        const sectionValue = await getSectionValue();
        tileData.value = sectionValue?.aliased_data[props.nodegroupAlias];

        const currentPosition = await getHierarchicalData([
            props.resourceInstanceId!,
        ]);

        schemeId.value = currentPosition.data[0]?.parents?.[0]?.[0]?.id;

        hierarchicalData.value = currentPosition.data[0]?.parents?.map(
            (parent: SearchResultItem) => ({ searchResults: parent }),
        );
    } else if (shouldCreateNewTile) {
        const blankTileData = await fetchTileData(
            props.graphSlug,
            props.nodegroupAlias,
        );
        tileData.value = [
            blankTileData as unknown as ConceptClassificationStatus,
        ];
    }

    if (hierarchicalData.value && tileData.value) {
        for (const datum of hierarchicalData.value) {
            const parentConceptResourceId =
                datum.searchResults[datum.searchResults.length - 2].id;
            const parentConceptTile = tileData.value.find((tile) => {
                const ascribedValues =
                    tile.aliased_data
                        .classification_status_ascribed_classification
                        .node_value;
                return ascribedValues?.some(
                    (value) => value.resourceId === parentConceptResourceId,
                );
            });
            if (parentConceptTile) {
                datum.tileid = parentConceptTile.tileid;
            } else if (topConceptOfTileId.value) {
                datum.tileid = topConceptOfTileId.value;
                datum.isTopConcept = true;
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

        const topConceptOfValue = await fetchLingoResourcePartial(
            props.graphSlug,
            props.resourceInstanceId as string,
            "top_concept_of",
        );
        topConceptOfTileId.value =
            topConceptOfValue.aliased_data.top_concept_of[0]?.tileid;

        return sectionValue;
    } catch (error) {
        fetchError.value = error;
    }
}
</script>

<template>
    <Skeleton
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
            :component-name="props.componentName"
            :data="hierarchicalData"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
            :resource-instance-id="props.resourceInstanceId"
            :section-title="props.sectionTitle"
            :scheme="schemeId"
        />
        <HierarchicalPositionEditor
            v-else-if="mode === EDIT"
            :component-name="props.componentName"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
            :resource-instance-id="props.resourceInstanceId"
            :section-title="props.sectionTitle"
            :scheme="schemeId"
            :tile-data="
                tileData!.find((tileDatum) => {
                    if (shouldCreateNewTile) {
                        return !tileDatum.tileid;
                    }

                    return tileDatum.tileid === props.tileId;
                })
            "
            :tile-id="props.tileId"
        />
    </template>
</template>
