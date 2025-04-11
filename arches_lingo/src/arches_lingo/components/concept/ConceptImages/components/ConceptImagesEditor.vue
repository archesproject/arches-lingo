<script setup lang="ts">
import { inject, onMounted, ref, useTemplateRef, watch } from "vue";

import { Form, type FormSubmitEvent } from "@primevue/forms";

import FileListWidget from "@/arches_component_lab/widgets/FileListWidget/FileListWidget.vue";

//import { createLingoResource, fetchLingoResource, upsertLingoTile } from "@/arches_lingo/api.ts";

import type { Component, Ref } from "vue";
//import type { FormSubmitEvent } from "@primevue/forms";

import type {
    ConceptImages,
    DigitalObjectInstance,
} from "@/arches_lingo/types.ts";
import { EDIT } from "@/arches_lingo/constants.ts";
import NonLocalizedStringWidget from "@/arches_component_lab/widgets/NonLocalizedStringWidget/NonLocalizedStringWidget.vue";
import { fetchLingoResource, updateLingoResource } from "@/arches_lingo/api.ts";

const props = defineProps<{
    tileData: ConceptImages | undefined;
    componentName: string;
    sectionTitle: string;
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId?: string;
    tileId?: string;
}>();

const resource = ref<DigitalObjectInstance>();

onMounted(async () => {
    if (props.resourceInstanceId) {
        //resource.value = await getConceptImageResource(props.resourceInstanceId);
    }
});

const componentEditorFormRef = inject<Ref<Component | null>>(
    "componentEditorFormRef",
);

const openEditor =
    inject<(componentName: string, tileid?: string) => void>("openEditor");
const refreshReportSection = inject<(componentName: string) => void>(
    "refreshReportSection",
);

const formRef = useTemplateRef("form");
watch(
    () => formRef.value,
    (formComponent) => (componentEditorFormRef!.value = formComponent),
);

async function getConceptImageResource(resourceInstanceId: string) {
    try {
        return await fetchLingoResource(
            "digital_object_rdm_system",
            resourceInstanceId,
        );
    } catch (error) {
        console.error(error);
    }
}

async function save(e: FormSubmitEvent) {
    try {
        const formData = Object.fromEntries(
            Object.entries(e.states).map(([key, state]) => [key, state.value]),
        );
        console.log("hey, formdata!", formData);
        let updatedTileId;

        if (resource.value) {
            await updateLingoResource(
                props.graphSlug,

            )
        }

        openEditor!(props.componentName, updatedTileId);
    } catch (error) {
        console.error(error);
    } finally {
        refreshReportSection!(props.componentName);
    }
}

document.addEventListener("openConceptImagesEditor", async (e) => {
    const customEvent = e as CustomEvent;
    console.log('foo event triggered', customEvent.detail.resourceInstanceId);
    resource.value = await getConceptImageResource(customEvent.detail.resourceInstanceId);

});
</script>

<template>
    <h3>{{ props.sectionTitle }}</h3>
    <Form
        ref="form"
        enctype="multipart/form-data"
        action="/test"
        method="post"
        @submit="save"
    >
        <NonLocalizedStringWidget
            node-alias="name_content"
            graph-slug="digital_object_rdm_system"
            :mode="EDIT"
            :initial-value="resource?.aliased_data.name.aliased_data.name_content
                "
        />
        <NonLocalizedStringWidget
            node-alias="statement_content"
            graph-slug="digital_object_rdm_system"
            :mode="EDIT"
            :initial-value="resource?.aliased_data.statement?.aliased_data.statement_content
                "
        />
        <FileListWidget
            node-alias="content"
            graph-slug="digital_object_rdm_system"
            :initial-value="resource?.aliased_data?.content?.aliased_data.content"
            :mode="EDIT"
            class="conceptImage"
        />
    </Form>
</template>
