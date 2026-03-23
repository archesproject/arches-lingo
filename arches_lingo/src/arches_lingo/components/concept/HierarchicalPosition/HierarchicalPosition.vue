<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import HierarchicalPositionViewer from "@/arches_lingo/components/concept/HierarchicalPosition/components/HierarchicalPositionViewer.vue";
import HierarchicalPositionEditor from "@/arches_lingo/components/concept/HierarchicalPosition/components/HierarchicalPositionEditor.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

import { fetchTileData } from "@/arches_component_lab/generics/GenericCard/api.ts";
import { useResourceStore } from "@/arches_lingo/composables/useResourceStore.ts";
import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";

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

const emit = defineEmits<{
    (event: "update:isEditorLoading", value: boolean): void;
}>();

const resourceStore = useResourceStore();
const conceptStore = useConceptStore();

const fetchError = ref();
const hierarchicalData = ref<SearchResultHierarchy[]>([]);
const schemeId = ref<string>();
const tileData = ref<ConceptClassificationStatus[]>();
const isTopConcept = ref(false);

const shouldCreateNewTile = computed(
    () => props.mode === EDIT && !props.tileId,
);
const isLoading = ref(
    Boolean(props.resourceInstanceId) || shouldCreateNewTile.value,
);

const activeTileData = computed((): ConceptClassificationStatus | undefined => {
    if (shouldCreateNewTile.value) {
        return tileData.value?.find((tileDatum) => !tileDatum.tileid);
    }
    return tileData.value?.find(
        (tileDatum) => tileDatum.tileid === props.tileId,
    );
});

onMounted(async () => {
    schemeId.value =
        resourceStore.resource.value?.aliased_data?.part_of_scheme.aliased_data
            .part_of_scheme?.details[0]?.resource_id ??
        conceptStore.getParentPaths(props.resourceInstanceId ?? "")[0]?.[0]?.id;

    if (shouldCreateNewTile.value) {
        const blankTileData = await fetchTileData(
            props.graphSlug,
            props.nodegroupAlias,
        );
        tileData.value = [
            blankTileData as unknown as ConceptClassificationStatus,
        ];
        isLoading.value = false;
        if (props.mode === EDIT) emit("update:isEditorLoading", false);
    }
});

watch(
    [() => resourceStore.resource.value, () => resourceStore.error.value],
    async ([resource, storeError]) => {
        if (storeError) {
            fetchError.value = storeError;
            isLoading.value = false;
            if (props.mode === EDIT) emit("update:isEditorLoading", false);
            return;
        }

        if (!resource || !props.resourceInstanceId || shouldCreateNewTile.value)
            return;

        try {
            isTopConcept.value = Boolean(resource.aliased_data?.top_concept_of);

            if (isTopConcept.value) {
                isLoading.value = false;
                if (props.mode === EDIT) emit("update:isEditorLoading", false);
                return;
            }

            tileData.value = resource.aliased_data?.[
                props.nodegroupAlias
            ] as ConceptClassificationStatus[];

            await conceptStore.initialize();

            const paths = conceptStore.getParentPaths(
                props.resourceInstanceId!,
            );

            schemeId.value = paths[0]?.[0]?.id;
            hierarchicalData.value = paths.map((path) => ({
                searchResults: path as SearchResultItem[],
            }));

            for (const datum of hierarchicalData.value) {
                const parentId =
                    datum.searchResults[datum.searchResults.length - 2].id;
                const match = tileData.value?.find((tile) =>
                    tile.aliased_data.classification_status_ascribed_classification.node_value?.some(
                        (nodeValue) => nodeValue.resourceId === parentId,
                    ),
                );
                if (match) datum.tileid = match.tileid;
            }
        } catch (error) {
            fetchError.value = error;
        } finally {
            isLoading.value = false;
            if (props.mode === EDIT) emit("update:isEditorLoading", false);
        }
    },
    { immediate: true },
);
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
    <template v-else-if="!isTopConcept">
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
            :tile-data="activeTileData"
            :tile-id="props.tileId"
        />
    </template>
</template>
