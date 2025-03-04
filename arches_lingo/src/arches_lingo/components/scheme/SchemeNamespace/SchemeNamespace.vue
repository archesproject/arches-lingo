<script setup lang="ts">
import { onMounted, ref } from "vue";

import ProgressSpinner from "primevue/progressspinner";

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

onMounted(async () => {
    if (
        props.resourceInstanceId &&
        (props.mode === VIEW || !shouldCreateNewTile)
    ) {
        const sectionValue = await getSectionValue();
        tileData.value = sectionValue[props.nodegroupAlias];
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
        console.error(error);
    }
}
</script>

<template>
    <ProgressSpinner
        v-if="isLoading"
        style="width: 100%"
    />

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
