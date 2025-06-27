<script setup lang="ts">
import { onMounted, ref } from "vue";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import SchemeLicenseViewer from "@/arches_lingo/components/scheme/SchemeLicense/components/SchemeLicenseViewer.vue";
import SchemeLicenseEditor from "@/arches_lingo/components/scheme/SchemeLicense/components/SchemeLicenseEditor.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

import { fetchLingoResourcePartial } from "@/arches_lingo/api.ts";

import type { DataComponentMode, SchemeRights } from "@/arches_lingo/types";

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
const tileData = ref<SchemeRights>();
const fetchError = ref();

const shouldCreateNewTile = Boolean(props.mode === EDIT && !props.tileId);

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
        <SchemeLicenseViewer
            v-if="mode === VIEW"
            :tile-data="tileData"
            :component-name="props.componentName"
            :graph-slug="props.graphSlug"
            :section-title="props.sectionTitle"
        />
        <SchemeLicenseEditor
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
