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

async function save(e: FormSubmitEvent) {
    try {
        const formData = Object.fromEntries(
            Object.entries(e.states).map(([key, state]) => [key, state.value]),
        );
        console.log("hey, formdata!", formData);
        let updatedTileId;

        if (resource.value) {
            if (!resource.value.aliased_data.name) {
                resource.value.aliased_data.name = {
                    aliased_data: {
                        name_content: formData.name_content,
                    },
                };
            } else {
                resource.value.aliased_data.name.aliased_data.name_content =
                    formData.name_content;
            }
            if (!resource.value.aliased_data.statement) {
                resource.value.aliased_data.statement = {
                    aliased_data: {
                        statement_content: formData.statement_content,
                    },
                };
            } else {
                resource.value.aliased_data.statement.aliased_data.statement_content =
                    formData.statement_content;
            }

            // file do not respect json.stringify
            const fileJsonObjects = formData.content.newFiles.map((file) => {
                return {
                    name: file.name.replace(/ /g, "_"),
                    accepted: file.accepted,
                    height: file.height,
                    lastModified: file.lastModified,
                    size: file.size,
                    status: file.status,
                    type: file.type,
                    width: file.width,
                    url: null,
                    file_id: null,
                    content: URL.createObjectURL(file),
                    error: file.error,
                };
            });

            if (!resource.value.aliased_data.content) {
                resource.value.aliased_data.content = {
                    aliased_data: {
                        content: fileJsonObjects,
                    },
                };
            } else {
                resource.value.aliased_data.content.aliased_data.content =
                    fileJsonObjects;
            }
            const contentTile =
                resource.value.aliased_data.content.aliased_data;

            contentTile.content = [...contentTile.content, ...fileJsonObjects];
            contentTile.content.filter(
                (file) => !formData.content.deletedFiles.includes(file),
            );
            const formdata = new FormData();
            const isJsonObject = (testObject: unknown) =>
                testObject &&
                typeof testObject === "object" &&
                !Array.isArray(testObject) &&
                Object.prototype.toString.call(testObject) ===
                "[object Object]";

            for (const [key, val] of Object.entries(resource.value)) {
                if (["name", "descriptors"].includes(key)) {
                    // TODO: avoid need to skip these
                    continue;
                }
                if (isJsonObject(val)) {
                    formdata.append(key, new Blob([JSON.stringify(val)], {
                        type: "application/json",
                    }));
                } else {
                    formdata.append(key, val);
                }
            }
            for (const file of formData.content.newFiles) {
                formdata.append(
                    // future: change(?)
                    `file-list_${"f522c448-1778-11ef-b270-0a58a9feac02"}`,
                    file,
                );
            }
            await updateLingoResource(
                "digital_object_rdm_system",
                resource.value.resourceinstanceid,
                undefined,
                formdata,
            );
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
    try {
        resource.value = await fetchLingoResource(
            "digital_object_rdm_system",
            customEvent.detail.resourceInstanceId,
        );
    } catch (error) {
        console.error(error);
    }
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
            :initial-value="resource?.aliased_data?.content?.aliased_data.content
                "
            :mode="EDIT"
            class="conceptImage"
        />
    </Form>
</template>
