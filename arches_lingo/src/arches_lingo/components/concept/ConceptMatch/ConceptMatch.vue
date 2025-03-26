<script setup lang="ts">
import { onMounted, ref } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import ProgressSpinner from "primevue/progressspinner";

import ConceptMatchEditor from "@/arches_lingo/components/concept/ConceptMatch/components/ConceptMatchEditor.vue";
import ConceptMatchViewer from "@/arches_lingo/components/concept/ConceptMatch/components/ConceptMatchViewer.vue";

import {
    DEFAULT_ERROR_TOAST_LIFE,
    EDIT,
    ERROR,
    VIEW,
} from "@/arches_lingo/constants.ts";

import { fetchLingoResourcePartial } from "@/arches_lingo/api.ts";

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

const toast = useToast();
const { $gettext } = useGettext();

const isLoading = ref(true);
const tileData = ref<ConceptMatchStatus[]>([]);
const schemeId = ref<string>();

const shouldCreateNewTile = Boolean(props.mode === EDIT && !props.tileId);

onMounted(async () => {
    if (
        props.resourceInstanceId &&
        (props.mode === VIEW || !shouldCreateNewTile)
    ) {
        const sectionValue = await getSectionValue();
        tileData.value = sectionValue[props.nodegroupAlias];
    }

    schemeId.value = await getSchemeId();
    isLoading.value = false;
});

async function getSectionValue() {
    try {
        const sectionValue = await fetchLingoResourcePartial(
            props.graphSlug,
            props.resourceInstanceId as string,
            props.nodegroupAlias,
        );
        for (const value of sectionValue[props.nodegroupAlias]) {
            value["uri"] = await getURI(
                value["match_status_ascribed_comparate"][0]["resourceId"],
            );
        }
        return sectionValue;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to fetch data."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

async function getURI(resourceId: string) {
    const uriData = await fetchLingoResourcePartial(
        props.graphSlug,
        resourceId,
        "uri",
    );
    if (!uriData.uri) {
        return null;
    }
    return JSON.parse(uriData.uri.uri_content.replace(/'/g, '"'));
}

async function getSchemeId() {
    const partOfScheme = await fetchLingoResourcePartial(
        props.graphSlug,
        props.resourceInstanceId as string,
        "part_of_scheme",
    );

    return partOfScheme.part_of_scheme?.part_of_scheme?.[0]?.resourceId;
}
</script>

<template>
    <ProgressSpinner
        v-if="isLoading"
        style="width: 100%"
    />

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
                tileData.find((tileDatum) => tileDatum.tileid === props.tileId)
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
