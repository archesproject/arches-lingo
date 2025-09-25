<script setup lang="ts">
import { onMounted, ref } from "vue";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import SchemeNamespaceEditor from "@/arches_lingo/components/scheme/SchemeNamespace/components/SchemeNamespaceEditor.vue";
import SchemeNamespaceViewer from "@/arches_lingo/components/scheme/SchemeNamespace/components/SchemeNamespaceViewer.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

import { fetchTileData } from "@/arches_component_lab/generics/GenericCard/api.ts";
import { fetchLingoResourcePartial } from "@/arches_lingo/api.ts";

import type {
    SchemeNamespace,
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

const shouldCreateNewTile = Boolean(props.mode === EDIT && !props.tileId);

const isLoading = ref(true);
const tileData = ref<SchemeNamespace>();
const fetchError = ref();

onMounted(async () => {
    if (
        props.resourceInstanceId &&
        (props.mode === VIEW || !shouldCreateNewTile)
    ) {
        const sectionValue = await getSectionValue();
        tileData.value = sectionValue.aliased_data[props.nodegroupAlias];
    } else if (shouldCreateNewTile) {
        const blankTileData = await fetchTileData(
            props.graphSlug,
            props.nodegroupAlias,
        );
        tileData.value = blankTileData as unknown as SchemeNamespace;
    }
    isLoading.value = false;
});

async function getSectionValue() {
    try {
        return await fetchLingoResourcePartial(
            props.graphSlug,
            props.resourceInstanceId as string,
            props.nodegroupAlias,
        );
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
        <SchemeNamespaceViewer
            v-if="mode === VIEW"
            :component-name="props.componentName"
            :graph-slug="props.graphSlug"
            :resource-instance-id="props.resourceInstanceId"
            :section-title="props.sectionTitle"
            :tile-data="tileData"
        />
        <SchemeNamespaceEditor
            v-else-if="mode === EDIT"
            :component-name="props.componentName"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
            :resource-instance-id="props.resourceInstanceId"
            :section-title="props.sectionTitle"
            :tile-data="tileData"
            :tile-id="props.tileId"
        />
    </template>
</template>
