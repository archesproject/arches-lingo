<script setup lang="ts">
import { onMounted, ref } from "vue";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import ConceptRelationshipEditor from "@/arches_lingo/components/concept/ConceptRelationship/components/ConceptRelationshipEditor.vue";
import ConceptRelationshipViewer from "@/arches_lingo/components/concept/ConceptRelationship/components/ConceptRelationshipViewer.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

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

onMounted(async () => {
    if (props.resourceInstanceId) {
        const sectionValue = await getSectionValue();
        tileData.value = sectionValue?.data;
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
            :tile-data="tileData"
            :section-title="props.sectionTitle"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
            :component-name="props.componentName"
        />
        <ConceptRelationshipEditor
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
