<script setup lang="ts">
import { onMounted, ref, watch } from "vue";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import ConceptLabelEditor from "@/arches_lingo/components/concept/ConceptLabel/components/ConceptLabelEditor.vue";
import ConceptLabelViewer from "@/arches_lingo/components/concept/ConceptLabel/components/ConceptLabelViewer.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

import { fetchTileData } from "@/arches_component_lab/generics/GenericCard/api.ts";
import { useResourceStore } from "@/arches_lingo/composables/useResourceStore.ts";

import type {
    AppellativeStatus,
    DataComponentMode,
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

const isDataLoading = ref(true);

const tileData = ref<AppellativeStatus[]>([]);
const fetchError = ref();

const shouldCreateNewTile = Boolean(props.mode === EDIT && !props.tileId);

const store = useResourceStore();

watch(
    [() => store.resource.value, () => store.error.value],
    ([resource, storeError]) => {
        if (storeError) {
            fetchError.value = storeError;
            isDataLoading.value = false;
            return;
        }
        if (resource && props.resourceInstanceId && !shouldCreateNewTile) {
            tileData.value =
                resource.aliased_data?.[props.nodegroupAlias] ?? [];
            isDataLoading.value = false;
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
        tileData.value = [blankTileData as unknown as AppellativeStatus];
        isDataLoading.value = false;
    } else if (!props.resourceInstanceId) {
        isDataLoading.value = false;
    }
});
</script>

<template>
    <Skeleton
        v-if="isDataLoading"
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
        <ConceptLabelViewer
            v-if="mode === VIEW"
            :component-name="props.componentName"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
            :resource-instance-id="props.resourceInstanceId"
            :section-title="props.sectionTitle"
            :tile-data="tileData"
        />
        <ConceptLabelEditor
            v-else-if="mode === EDIT"
            :component-name="props.componentName"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
            :resource-instance-id="props.resourceInstanceId"
            :section-title="props.sectionTitle"
            :tile-data="
                tileData.find((tileDatum) => {
                    if (shouldCreateNewTile) {
                        return !tileDatum.tileid;
                    }

                    return tileDatum.tileid === props.tileId;
                })
            "
            :tile-id="props.tileId"
            @update:is-loading="emit('update:isEditorLoading', $event)"
        />
    </template>
</template>
