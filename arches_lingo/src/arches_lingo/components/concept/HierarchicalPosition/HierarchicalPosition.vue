<script setup lang="ts">
import { onMounted, ref, watch} from "vue";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import HierarchicalPositionViewer from "@/arches_lingo/components/concept/HierarchicalPosition/components/HierarchicalPositionViewer.vue";
import HierarchicalPositionEditor from "@/arches_lingo/components/concept/HierarchicalPosition/components/HierarchicalPositionEditor.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

import { fetchTileData } from "@/arches_component_lab/generics/GenericCard/api.ts";
import { fetchConceptResources } from "@/arches_lingo/api.ts";
import { useResourceStore } from "@/arches_lingo/composables/useResourceStore.ts";
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

const store = useResourceStore();
let positionInitialized = false;

watch(
    [() => store.resource.value, () => store.error.value],
    async ([resource, storeError]) => {
        if (storeError) {
            fetchError.value = storeError;
            isLoading.value = false;
            return;
        }
        if (
            !resource ||
            !props.resourceInstanceId ||
            shouldCreateNewTile ||
            positionInitialized
        )
            return;
        positionInitialized = true;

        try {
            // Read classification_status and top_concept_of from the store
            tileData.value = resource.aliased_data?.[props.nodegroupAlias];
            topConceptOfTileId.value =
                resource.aliased_data?.top_concept_of?.[0]?.tileid;

            // Still need the search endpoint for hierarchy path data
            const currentPosition = await getHierarchicalData([
                props.resourceInstanceId!,
            ]);

            schemeId.value = currentPosition?.data[0]?.parents?.[0]?.[0]?.id;

            hierarchicalData.value =
                currentPosition?.data[0]?.parents?.map(
                    (parent: SearchResultItem) => ({
                        searchResults: parent,
                    }),
                ) ?? [];

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
                            (value) =>
                                value.resourceId === parentConceptResourceId,
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
        } catch (error) {
            fetchError.value = error;
        } finally {
            isLoading.value = false;
        }
    },
    { immediate: true },
);

onMounted(async () => {
    if (shouldCreateNewTile) {
        const blankTileData = await fetchTileData(
            props.graphSlug,
            props.nodegroupAlias,
        );
        tileData.value = [
            blankTileData as unknown as ConceptClassificationStatus,
        ];
        isLoading.value = false;
    } else if (!props.resourceInstanceId) {
        isLoading.value = false;
    }
});

async function getHierarchicalData(conceptIds: string[]) {
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
