<script setup lang="ts">
import { onMounted, ref } from "vue";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import SchemeNoteEditor from "@/arches_lingo/components/scheme/SchemeNote/components/SchemeNoteEditor.vue";
import SchemeNoteViewer from "@/arches_lingo/components/scheme/SchemeNote/components/SchemeNoteViewer.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

import { fetchTileData } from "@/arches_component_lab/generics/GenericCard/api.ts";
import { fetchLingoResourcePartial } from "@/arches_lingo/api.ts";

import type {
    DataComponentMode,
    SchemeStatement,
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
const tileData = ref<SchemeStatement[]>([]);
const fetchError = ref();

const shouldCreateNewTile = Boolean(props.mode === EDIT && !props.tileId);

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
        tileData.value = [blankTileData as unknown as SchemeStatement];
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
        <SchemeNoteViewer
            v-if="mode === VIEW"
            :tile-data="tileData"
            :graph-slug="props.graphSlug"
            :component-name="props.componentName"
            :section-title="props.sectionTitle"
            :nodegroup-alias="props.nodegroupAlias"
        />
        <SchemeNoteEditor
            v-else-if="mode === EDIT"
            :tile-data="
                tileData.find((tileDatum) => {
                    if (shouldCreateNewTile) {
                        return !tileDatum.tileid;
                    }

                    return tileDatum.tileid === props.tileId;
                })
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
