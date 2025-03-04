<script setup lang="ts">
import { onMounted, ref } from "vue";

import ProgressSpinner from "primevue/progressspinner";

import SchemeLabelEditor from "@/arches_lingo/components/scheme/SchemeLabel/components/SchemeLabelEditor.vue";
import SchemeLabelViewer from "@/arches_lingo/components/scheme/SchemeLabel/components/SchemeLabelViewer.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

import { fetchLingoResourcePartial } from "@/arches_lingo/api.ts";

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

const isLoading = ref(true);
const tileData = ref<AppellativeStatus[]>([]);

const shouldCreateNewTile = Boolean(props.mode === EDIT && !props.tileId);

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
        <SchemeLabelViewer
            v-if="mode === VIEW"
            :tile-data="tileData"
            :section-title="props.sectionTitle"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
            :component-name="props.componentName"
        />
        <SchemeLabelEditor
            v-else-if="mode === EDIT"
            :tile-data="
                tileData.find((tileDatum) => tileDatum.tileid === props.tileId)
            "
            :component-name="props.componentName"
            :section-title="props.sectionTitle"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
            :resource-instance-id="props.resourceInstanceId"
            :tile-id="props.tileId"
        />
    </template>
</template>
