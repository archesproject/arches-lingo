<script setup lang="ts">
import { inject, nextTick, onMounted, ref, useTemplateRef, watch } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import { Form } from "@primevue/forms";

import Skeleton from "primevue/skeleton";

import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import { DIGITAL_OBJECT_GRAPH_SLUG } from "@/arches_lingo/components/concept/ConceptImages/components/constants.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    EDIT,
    ERROR,
} from "@/arches_lingo/constants.ts";

import {
    createFormDataForFileUpload,
    addDigitalObjectToConceptImageCollection,
    createDigitalObject,
} from "@/arches_lingo/components/concept/ConceptImages/components/utils.ts";

import {
    fetchLingoResource,
    updateLingoResource,
    updateLingoResourceFromForm,
} from "@/arches_lingo/api.ts";

import type { Component, Ref } from "vue";
import type { FormSubmitEvent } from "@primevue/forms";
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

const { $gettext } = useGettext();
const toast = useToast();

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
const isSaving = ref(false);

onMounted(() => {
    document.addEventListener(
        "openConceptImagesEditor",
        getDigitalObjectInstance,
    );
    document.dispatchEvent(new Event("conceptImagesEditor:ready"));
});

watch(
    () => formRef.value,
    (formComponent) => (componentEditorFormRef!.value = formComponent),
);

async function getDigitalObjectInstance(
    // custom event type is from global dom
    // eslint-disable-next-line no-undef
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
    isSaving.value = true;

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
        const fileJsonObjects =
            submittedFormData.content.newFiles?.map((file: File) => {
                return {
                    name: file.name.replace(/ /g, "_"),
                    lastModified: file.lastModified,
                    size: file.size,
                    type: file.type,
                    url: null,
                    file_id: null,
                    content: URL.createObjectURL(file),
                };
            }) ?? [];

        if (!digitalObjectInstanceAliases.content) {
            digitalObjectInstanceAliases.content = {
                aliased_data: {
                    content: fileJsonObjects,
                },
            };
        } else {
            // disabling this block as it breaks typescript. It should be re-enabled as part of the
            // effort to get image editing working again.
            // digitalObjectInstanceAliases.content.aliased_data.content = [
            //     ...(digitalObjectInstanceAliases.content.aliased_data.content?.node_value ?? []),
            //     ...fileJsonObjects,
            // ];
        }
        const contentTile = digitalObjectInstanceAliases.content.aliased_data;

        contentTile.content.filter(
            (file) => !submittedFormData.content?.deletedFiles?.includes(file),
        );

        // this fork was requested because the multipartjson parser is unstable
        // if files go one way, if no files go the traditional way
        if (submittedFormData.content.newFiles?.length) {
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
        refreshReportSection!(props.componentName);
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to save data."),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isSaving.value = false;
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
    <Skeleton
        v-show="isSaving"
        style="width: 100%"
    />
    <div v-show="!isSaving">
        <div class="form-header">
            <h3>{{ props.sectionTitle }}</h3>
            <div class="form-description">
                {{ $gettext("Add images, image titles, and descriptions to help illustrate features of the concept.") }}
            </div>
        </div>

         <div class="form-container">
            <Form
                v-if="digitalObjectLoaded"
                ref="form"
                @submit="save"
                @reset="resetForm"
            >
                <div class="widget-container column">
                    <GenericWidget
                        node-alias="name_content"
                        graph-slug="digital_object_rdm_system"
                        :mode="EDIT"
                        :aliased-node-data="
                            digitalObjectResource?.aliased_data.name?.aliased_data
                                .name_content
                        "
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        node-alias="statement_content"
                        graph-slug="digital_object_rdm_system"
                        :mode="EDIT"
                        :aliased-node-data="
                            digitalObjectResource?.aliased_data.statement?.aliased_data
                                .statement_content
                        "
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        node-alias="content"
                        graph-slug="digital_object_rdm_system"
                        :aliased-node-data="
                            digitalObjectResource?.aliased_data?.content?.aliased_data
                                .content
                        "
                        :mode="EDIT"
                        :should-show-label="false"
                    />
                </div>
            </Form>
        </div>
    </div>
</template>
<style scoped>
.widget-container {
    display: flex; 
    gap: .25rem; 
    padding: .5rem 0rem 0.25rem 0rem;
    color: var(--p-header-item-label);
}

.form-header {
    padding-top: 0rem;
    padding-bottom: 1rem;
    background: var(--p-header-background);
    border-bottom: 0.06rem solid var(--p-header-border);
    min-height: 5.5rem;
}

.form-header h3 {
    margin: 0;
    padding: 0.5rem 1rem 0 1rem;
}

.form-container {
    padding: 0.5rem 1rem;
}

.form-description {
    padding: 0.125rem 1rem;
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
    margin-inline-end: 0.25rem;
}

.column {
    flex-direction: column;
}

:deep(.p-inputtext) {
    border-radius: .125rem;
}

:deep(.p-textarea) {
    border-radius: .125rem;
}

:deep(.p-treeselect) {
    border-radius: .125rem;
}

:deep(.p-multiselect) {
    border-radius: .125rem;
}

:deep(.p-fileupload-advanced) {
    border: none;
}

:deep(.p-fileupload-header) {
    padding: 0;
}

:deep(.p-fileupload-file) {
    flex-direction: column;
    align-items: flex-start;
    padding: 0;
}

:deep(.p-fileupload-file-info ) {
    flex-direction: row;
}

:deep(.p-fileupload-content) {
    padding: 0;
    margin-top: 1rem;
}

</style>
