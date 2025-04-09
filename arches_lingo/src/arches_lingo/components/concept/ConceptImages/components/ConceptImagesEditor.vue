<script setup lang="ts">
import { inject, nextTick, ref, useTemplateRef, watch } from "vue";

import { Form, type FormSubmitEvent } from "@primevue/forms";
import FileListWidget from "@/arches_component_lab/widgets/FileListWidget/FileListWidget.vue";
import NonLocalizedStringWidget from "@/arches_component_lab/widgets/NonLocalizedStringWidget/NonLocalizedStringWidget.vue";
import { DIGITAL_OBJECT_GRAPH_SLUG } from "@/arches_lingo/components/concept/ConceptImages/components/constants.ts";
import {
    createFormDataForFileUpload,
    addDigitalObjectToConceptImageCollection,
    createDigitalObject,
} from "@/arches_lingo/components/concept/ConceptImages/components/utils.ts";
import { EDIT } from "@/arches_lingo/constants.ts";
import {
    fetchLingoResource,
    updateLingoResource,
    updateLingoResourceFromForm,
} from "@/arches_lingo/api.ts";

import type { Component, Ref } from "vue";
import type {
    ConceptImages,
    DigitalObjectInstance,
    DigitalObjectInstanceAliases,
} from "@/arches_lingo/types.ts";

const props = defineProps<{
    tileData: ConceptImages | undefined;
    componentName: string;
    sectionTitle: string;
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId?: string;
    tileId?: string;
}>();

const digitalObjectResource = ref<DigitalObjectInstance>();
const digitalObjectLoaded = ref(false);

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

document.addEventListener("openConceptImagesEditor", getDigitalObjectInstance);

async function getDigitalObjectInstance(
    e?: CustomEventInit<{ resourceInstanceId?: string }>,
) {
    const customEvent = e as CustomEvent;
    try {
        if (customEvent?.detail.resourceInstanceId === undefined) {
            digitalObjectResource.value = undefined;
        } else {
            digitalObjectResource.value = await fetchLingoResource(
                "digital_object_rdm_system",
                customEvent.detail.resourceInstanceId,
            );
        }
        digitalObjectLoaded.value = true;
    } catch (error) {
        console.error(error);
    }
}

async function save(e: FormSubmitEvent) {
    try {
        const submittedFormData = Object.fromEntries(
            Object.entries(e.states).map(([key, state]) => [key, state.value]),
        );

        let digitalObjectInstanceAliases: DigitalObjectInstanceAliases = {};

        if (digitalObjectResource.value) {
            digitalObjectInstanceAliases =
                digitalObjectResource.value.aliased_data;
        }

        if (submittedFormData.name_content) {
            if (!digitalObjectInstanceAliases.name) {
                digitalObjectInstanceAliases.name = {
                    aliased_data: {
                        name_content: submittedFormData.name_content,
                    },
                };
            } else {
                digitalObjectInstanceAliases.name.aliased_data.name_content =
                    submittedFormData.name_content;
            }
        }
        if (submittedFormData.statement_content) {
            if (!digitalObjectInstanceAliases.statement) {
                digitalObjectInstanceAliases.statement = {
                    aliased_data: {
                        statement_content: submittedFormData.statement_content,
                    },
                };
            } else {
                digitalObjectInstanceAliases.statement.aliased_data.statement_content =
                    submittedFormData.statement_content;
            }
        }

        // files do not respect json.stringify
        // ignore file type any - it's from primevue's FileUploadSelectEvent
        const fileJsonObjects = submittedFormData.content.newFiles.map(
            (file: any) => {
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
            },
        );

        if (!digitalObjectInstanceAliases.content) {
            digitalObjectInstanceAliases.content = {
                aliased_data: {
                    content: fileJsonObjects,
                },
            };
        } else {
            digitalObjectInstanceAliases.content.aliased_data.content = [
                ...(digitalObjectInstanceAliases.content.aliased_data.content ??
                    []),
                ...fileJsonObjects,
            ];
        }
        const contentTile = digitalObjectInstanceAliases.content.aliased_data;

        contentTile.content.filter(
            (file) => !submittedFormData.content.deletedFiles.includes(file),
        );

        // this fork was requested because the multipartjson parser is unstable
        // if files go one way, if no files go the traditional way
        if (submittedFormData.content.newFiles.length) {
            const formDataForDigitalObject = await createFormDataForFileUpload(
                digitalObjectResource as Ref<DigitalObjectInstance>,
                digitalObjectInstanceAliases,
                submittedFormData,
            );
            if (digitalObjectResource.value) {
                await updateLingoResourceFromForm(
                    DIGITAL_OBJECT_GRAPH_SLUG,
                    digitalObjectResource.value.resourceinstanceid,
                    formDataForDigitalObject,
                );
            } else {
                const digitalObject = await createDigitalObject(
                    formDataForDigitalObject,
                );
                digitalObjectResource.value = digitalObject;
                await addDigitalObjectToConceptImageCollection(
                    digitalObject,
                    props.graphSlug,
                    props.nodegroupAlias,
                    props.resourceInstanceId,
                );
            }
        } else {
            if (digitalObjectResource.value) {
                digitalObjectResource.value.aliased_data =
                    digitalObjectInstanceAliases;
                await updateLingoResource(
                    DIGITAL_OBJECT_GRAPH_SLUG,
                    digitalObjectResource.value.resourceinstanceid,
                    digitalObjectResource.value,
                );
            } else {
                const digitalObject = await createDigitalObject(
                    digitalObjectInstanceAliases,
                );
                digitalObjectResource.value = digitalObject;
                addDigitalObjectToConceptImageCollection(
                    digitalObject,
                    props.graphSlug,
                    props.nodegroupAlias,
                    props.resourceInstanceId,
                );
            }
        }

        // simulated click of the current resource
        modifyResource(digitalObjectResource?.value?.resourceinstanceid);
    } catch (error) {
        console.error(error);
        throw error;
    } finally {
        refreshReportSection!(props.componentName);
    }
}

function modifyResource(resourceInstanceId?: string) {
    openEditor!(props.componentName);

    nextTick(() => {
        const openConceptImagesEditor = new CustomEvent(
            "openConceptImagesEditor",
            { detail: { resourceInstanceId: resourceInstanceId } },
        );
        document.dispatchEvent(openConceptImagesEditor);
    });
}

function resetForm() {
    modifyResource(digitalObjectResource?.value?.resourceinstanceid);
}
</script>

<template>
    <h3>{{ props.sectionTitle }}</h3>
    <Form
        v-if="digitalObjectLoaded"
        ref="form"
        @submit="save"
        @reset="resetForm"
    >
        <NonLocalizedStringWidget
            node-alias="name_content"
            graph-slug="digital_object_rdm_system"
            :mode="EDIT"
            :initial-value="
                digitalObjectResource?.aliased_data.name?.aliased_data
                    .name_content
            "
        />
        <NonLocalizedStringWidget
            node-alias="statement_content"
            graph-slug="digital_object_rdm_system"
            :mode="EDIT"
            :initial-value="
                digitalObjectResource?.aliased_data.statement?.aliased_data
                    .statement_content
            "
        />
        <FileListWidget
            node-alias="content"
            graph-slug="digital_object_rdm_system"
            :initial-value="
                digitalObjectResource?.aliased_data?.content?.aliased_data
                    .content
            "
            :mode="EDIT"
            class="conceptImage"
        />
    </Form>
</template>
