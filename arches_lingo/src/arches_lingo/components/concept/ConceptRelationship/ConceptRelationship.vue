<script setup lang="ts">
import { watchEffect, ref } from "vue";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import ConceptRelationshipEditor from "@/arches_lingo/components/concept/ConceptRelationship/components/ConceptRelationshipEditor.vue";
import ConceptRelationshipViewer from "@/arches_lingo/components/concept/ConceptRelationship/components/ConceptRelationshipViewer.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

import { fetchTileData } from "@/arches_component_lab/generics/GenericCard/api.ts";
import { fetchConceptRelationships } from "@/arches_lingo/api.ts";

import type {
    ConceptRelationStatus,
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
const tileData = ref<ConceptRelationStatus[]>([]);
const fetchError = ref();
const schemeId = ref<string>();

const shouldCreateNewTile = Boolean(props.mode === EDIT && !props.tileId);

watchEffect(async () => {
    isLoading.value = true;
    const sectionValue = await getSectionValue();
    schemeId.value = sectionValue?.scheme_id;
    if (
        props.resourceInstanceId &&
        (props.mode === VIEW || !shouldCreateNewTile)
    ) {
        const sectionValue = await getSectionValue();
        tileData.value = sectionValue?.data;
        tileData.value = sectionValue?.data;
        schemeId.value = sectionValue.scheme_id;
    } else if (shouldCreateNewTile) {
        const blankTileData = await fetchTileData(
            props.graphSlug,
            props.nodegroupAlias,
        );
        tileData.value = [blankTileData as unknown as ConceptRelationStatus];
    }
    isLoading.value = false;
});

async function getSectionValue() {
    try {
        const sectionValue = await fetchConceptRelationships(
            props.resourceInstanceId as string,
            "associated",
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
        <ConceptRelationshipViewer
            v-if="mode === VIEW"
            :component-name="props.componentName"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
            :resource-instance-id="props.resourceInstanceId"
            :section-title="props.sectionTitle"
            :tile-data="tileData"
            :scheme="schemeId"
        />
        <ConceptRelationshipEditor
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
            :scheme="schemeId"
            :exclude="false"
        />
    </template>
</template>
