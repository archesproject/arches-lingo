<script setup lang="ts">
import { onMounted, ref } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import ProgressSpinner from "primevue/progressspinner";

import ConceptRelationshipEditor from "@/arches_lingo/components/concept/ConceptRelationship/components/ConceptRelationshipEditor.vue";
import ConceptRelationshipViewer from "@/arches_lingo/components/concept/ConceptRelationship/components/ConceptRelationshipViewer.vue";

import {
    DEFAULT_ERROR_TOAST_LIFE,
    EDIT,
    ERROR,
    VIEW,
} from "@/arches_lingo/constants.ts";

import { fetchLingoResourcePartial } from "@/arches_lingo/api.ts";

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

const toast = useToast();
const { $gettext } = useGettext();

const isLoading = ref(true);
const tileData = ref<ConceptRelationStatus[]>([]);
const schemeId = ref<string>();
const shouldCreateNewTile = Boolean(props.mode === EDIT && !props.tileId);

onMounted(async () => {
    if (
        props.resourceInstanceId &&
        (props.mode === VIEW || !shouldCreateNewTile)
    ) {
        const sectionValue = await getSectionValue();
        tileData.value = sectionValue.aliased_data[props.nodegroupAlias];;
    }
    schemeId.value = await getSchemeId();
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
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to fetch data."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

async function getSchemeId() {
    const partOfScheme = await fetchLingoResourcePartial(
        props.graphSlug,
        props.resourceInstanceId as string,
        "part_of_scheme",
    );

    return partOfScheme.aliased_data?.part_of_scheme?.aliased_data?.part_of_scheme?.[0]?.resourceId;
}
</script>

<template>
    <ProgressSpinner
        v-if="isLoading"
        style="width: 100%"
    />

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
            :scheme="schemeId"
            :component-name="props.componentName"
            :section-title="props.sectionTitle"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
            :resource-instance-id="props.resourceInstanceId"
            :tile-id="props.tileId"
        />
    </template>
</template>
