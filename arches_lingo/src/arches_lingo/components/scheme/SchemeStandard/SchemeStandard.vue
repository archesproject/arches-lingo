<script setup lang="ts">
import { onMounted, ref } from "vue";

import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";

import SchemeStandardViewer from "@/arches_lingo/components/scheme/SchemeStandard/components/SchemeStandardViewer.vue";
import SchemeStandardEditor from "@/arches_lingo/components/scheme/SchemeStandard/components/SchemeStandardEditor.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

import { fetchLingoResourcePartial } from "@/arches_lingo/api.ts";

import type {
    DataComponentMode,
    SchemeCreation,
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
const tileData = ref<SchemeCreation>();
const fetchError = ref();

const shouldCreateNewTile = Boolean(props.mode === EDIT && !props.tileId);

onMounted(async () => {
    if (
        props.resourceInstanceId &&
        (props.mode === VIEW || !shouldCreateNewTile)
    ) {
        const sectionValue = await getSectionValue();
        tileData.value = sectionValue.aliased_data[props.nodegroupAlias];
    } else {
        isLoading.value = false;
    }
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
    } finally {
        isLoading.value = false;
    }
}
</script>

<template>
    <ProgressSpinner
        v-if="isLoading"
        style="width: 100%"
    />

    <template v-else>
        <SchemeStandardViewer
            v-if="mode === VIEW"
            :tile-data="tileData"
            :graph-slug="props.graphSlug"
            :component-name="props.componentName"
            :section-title="props.sectionTitle"
        />
        <SchemeStandardEditor
            v-else-if="mode === EDIT"
            :tile-data="shouldCreateNewTile ? undefined : tileData"
            :section-title="props.sectionTitle"
            :graph-slug="props.graphSlug"
            :component-name="props.componentName"
            :resource-instance-id="props.resourceInstanceId"
            :nodegroup-alias="props.nodegroupAlias"
            :tile-id="props.tileId"
        />
        <Message
            v-if="fetchError"
            severity="error"
            size="small"
            >{{ fetchError.message }}
        </Message>
    </template>
</template>
