<script setup lang="ts">
import { onMounted, ref } from "vue";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import SchemeNamespaceEditor from "@/arches_lingo/components/scheme/SchemeNamespace/components/SchemeNamespaceEditor.vue";
import SchemeNamespaceViewer from "@/arches_lingo/components/scheme/SchemeNamespace/components/SchemeNamespaceViewer.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

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
const tileData = ref<SchemeNamespace | undefined>();
const fetchError = ref();

onMounted(async () => {
    if (
        props.resourceInstanceId &&
        (props.mode === VIEW || !shouldCreateNewTile)
    ) {
        const sectionValue = await getSectionValue();
        tileData.value = sectionValue.aliased_data[props.nodegroupAlias];
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
            :tile-data="tileData"
            :graph-slug="props.graphSlug"
            :component-name="props.componentName"
            :section-title="props.sectionTitle"
        />
        <SchemeNamespaceEditor
            v-else-if="mode === EDIT"
            :tile-data="shouldCreateNewTile ? undefined : tileData"
            :section-title="props.sectionTitle"
            :graph-slug="props.graphSlug"
            :component-name="props.componentName"
            :resource-instance-id="props.resourceInstanceId"
            :nodegroup-alias="props.nodegroupAlias"
            :tile-id="props.tileId"
        />
    </template>
</template>
