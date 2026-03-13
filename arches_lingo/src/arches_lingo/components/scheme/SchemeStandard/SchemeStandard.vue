<script setup lang="ts">
import { onMounted, ref, watch } from "vue";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import SchemeStandardViewer from "@/arches_lingo/components/scheme/SchemeStandard/components/SchemeStandardViewer.vue";
import SchemeStandardEditor from "@/arches_lingo/components/scheme/SchemeStandard/components/SchemeStandardEditor.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

import { fetchTileData } from "@/arches_component_lab/generics/GenericCard/api.ts";
import { useResourceStore } from "@/arches_lingo/composables/useResourceStore.ts";

import type {
    DataComponentMode,
    SchemeCreation,
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

const isLoading = ref(true);
const tileData = ref<SchemeCreation>();
const fetchError = ref();

const shouldCreateNewTile = Boolean(props.mode === EDIT && !props.tileId);

const store = useResourceStore();

watch(
    [() => store.resource.value, () => store.error.value],
    ([resource, storeError]) => {
        if (storeError) {
            fetchError.value = storeError;
            isLoading.value = false;
            return;
        }
        if (resource && props.resourceInstanceId && !shouldCreateNewTile) {
            tileData.value = resource.aliased_data?.[props.nodegroupAlias];
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
        tileData.value = blankTileData as unknown as SchemeCreation;
        isLoading.value = false;
    } else if (!props.resourceInstanceId) {
        isLoading.value = false;
    }
});
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
        <SchemeStandardViewer
            v-if="mode === VIEW"
            :component-name="props.componentName"
            :graph-slug="props.graphSlug"
            :resource-instance-id="props.resourceInstanceId"
            :section-title="props.sectionTitle"
            :tile-data="tileData"
        />
        <SchemeStandardEditor
            v-else-if="mode === EDIT"
            :component-name="props.componentName"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
            :resource-instance-id="props.resourceInstanceId"
            :section-title="props.sectionTitle"
            :tile-data="tileData"
            :tile-id="props.tileId"
            @update:is-loading="emit('update:isEditorLoading', $event)"
        />
    </template>
</template>
