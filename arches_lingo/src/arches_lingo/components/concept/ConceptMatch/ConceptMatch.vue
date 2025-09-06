<script setup lang="ts">
import { onMounted, ref } from "vue";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import ConceptMatchEditor from "@/arches_lingo/components/concept/ConceptMatch/components/ConceptMatchEditor.vue";
import ConceptMatchViewer from "@/arches_lingo/components/concept/ConceptMatch/components/ConceptMatchViewer.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

import { fetchTileData } from "@/arches_component_lab/generics/GenericCard/api.ts";
import { fetchConceptRelationships } from "@/arches_lingo/api.ts";

import type {
    ConceptMatchStatus,
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
const tileData = ref<ConceptMatchStatus[]>([]);
const schemeId = ref<string>();
const fetchError = ref();

const shouldCreateNewTile = Boolean(props.mode === EDIT && !props.tileId);

onMounted(async () => {
    if (
        props.resourceInstanceId &&
        (props.mode === VIEW || !shouldCreateNewTile)
    ) {
        const sectionValue = await getSectionValue();
        tileData.value = sectionValue?.data;
        schemeId.value = sectionValue?.scheme_id;
    } else if (shouldCreateNewTile) {
        const blankTileData = await fetchTileData(
            props.graphSlug,
            props.nodegroupAlias,
        );
        tileData.value = [blankTileData as unknown as ConceptMatchStatus];
    }
    isLoading.value = false;
});

async function getSectionValue() {
    try {
        const sectionValue = await fetchConceptRelationships(
            props.resourceInstanceId as string,
            "matched",
        );
        return sectionValue;
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
        <ConceptMatchViewer
            v-if="mode === VIEW"
            :tile-data="tileData"
            :section-title="props.sectionTitle"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
            :component-name="props.componentName"
        />
        <ConceptMatchEditor
            v-else-if="mode === EDIT"
            :tile-data="
                tileData.find((tileDatum) => {
                    if (shouldCreateNewTile) {
                        return !tileDatum.tileid;
                    }

                    return tileDatum.tileid === props.tileId;
                })
            "
            :scheme="schemeId"
            :exclude="true"
            :component-name="props.componentName"
            :section-title="props.sectionTitle"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
            :resource-instance-id="props.resourceInstanceId"
            :tile-id="props.tileId"
        />
    </template>
</template>
