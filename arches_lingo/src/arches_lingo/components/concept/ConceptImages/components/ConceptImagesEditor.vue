<script setup lang="ts">
import {
    inject,
    nextTick,
    onMounted,
    onUnmounted,
    ref,
    useTemplateRef,
    watch,
} from "vue";

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
import type { FileListValue } from "@/arches_component_lab/datatypes/file-list/types.ts";

import type {
    ConceptImages,
    DigitalObjectInstance,
    DigitalObjectInstanceAliases,
} from "@/arches_lingo/types.ts";

type PossiblyNewFile = FileListValue & {
    file?: File;
    name?: string;
    lastModified?: number;
    size?: number;
    type?: string;
};

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
const isLoading = ref(true);

onMounted(() => {
    document.addEventListener(
        "openConceptImagesEditor",
        getDigitalObjectInstance,
    );
    document.dispatchEvent(new Event("conceptImagesEditor:ready"));
});

onUnmounted(() => {
    document.removeEventListener(
        "openConceptImagesEditor",
        getDigitalObjectInstance,
    );
});

watch(
    () => formRef.value,
    (formComponent) => (componentEditorFormRef!.value = formComponent),
);

async function getDigitalObjectInstance(
    customEvent: CustomEvent<{ resourceInstanceId?: string }> | Event,
) {
    const typedEvent = customEvent as CustomEvent<{
        resourceInstanceId?: string;
    }>;
    try {
        if (typedEvent?.detail?.resourceInstanceId === undefined) {
            digitalObjectResource.value = undefined;
        } else {
            digitalObjectResource.value = await fetchLingoResource(
                "digital_object_rdm_system",
                typedEvent.detail.resourceInstanceId,
            );
        }
        digitalObjectLoaded.value = true;
        isLoading.value = false;
    } catch (error) {
        console.error(error);
    }
}

async function save(e: FormSubmitEvent) {
    isLoading.value = true;

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
            submittedFormData.content.node_value?.map(
                (file: PossiblyNewFile) => {
                    console.log(file.file);
                    if (!file?.file) {
                        return file;
                    } else {
                        return {
                            name: file.name?.replace(/ /g, "_"),
                            lastModified: file.lastModified,
                            size: file.size,
                            type: file.type,
                            url: null,
                            file_id: null,
                            content: URL.createObjectURL(file?.file),
                            altText: "Replaceable alt text",
                        };
                    }
                },
            ) ?? [];

        if (!digitalObjectInstanceAliases.content) {
            digitalObjectInstanceAliases.content = {
                aliased_data: {
                    content: {
                        node_value: [...fileJsonObjects],
                    } as unknown as FileListValue[],
                },
            };
        } else {
            digitalObjectInstanceAliases.content.aliased_data.content = {
                node_value: [...fileJsonObjects],
            } as unknown as FileListValue[];
        }

        // this fork was requested because the multipartjson parser is unstable
        // if files go one way, if no files go the traditional way
        if (submittedFormData.content.node_value?.length) {
            if (digitalObjectResource.value) {
                digitalObjectResource.value.aliased_data = {
                    ...digitalObjectInstanceAliases,
                };
            } else {
                digitalObjectResource.value = {
                    aliased_data: {
                        ...digitalObjectInstanceAliases,
                    },
                } as unknown as DigitalObjectInstance;
            }

            const formDataForDigitalObject = await createFormDataForFileUpload(
                digitalObjectResource as Ref<DigitalObjectInstance>,
                digitalObjectInstanceAliases,
                submittedFormData,
            );
            if (digitalObjectResource.value?.resourceinstanceid) {
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

        nextTick(() => {
            const openConceptImagesEditor = new CustomEvent(
                "openConceptImagesEditor",
                {
                    detail: {
                        resourceInstanceId:
                            digitalObjectResource.value?.resourceinstanceid,
                    },
                },
            );
            document.dispatchEvent(openConceptImagesEditor);
        });

        refreshReportSection!(props.componentName);
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to save data."),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
    }
}

function resetForm() {
    openEditor!(props.componentName);

    nextTick(() => {
        const openConceptImagesEditor = new CustomEvent(
            "openConceptImagesEditor",
            {
                detail: {
                    resourceInstanceId:
                        digitalObjectResource?.value?.resourceinstanceid,
                },
            },
        );
        document.dispatchEvent(openConceptImagesEditor);
    });
}
</script>

<template>
    <Skeleton
        v-show="isLoading"
        style="width: 100%; height: 100%"
    />
    <div v-show="!isLoading">
        <div class="form-header">
            <h3>{{ props.sectionTitle }}</h3>
            <div class="form-description">
                {{
                    $gettext(
                        "Add images, image titles, and descriptions to help illustrate features of the concept.",
                    )
                }}
            </div>
        </div>

        <div class="form-container">
            <Form
                v-if="!isLoading && digitalObjectLoaded"
                ref="form"
                @submit="save"
                @reset="resetForm"
            >
                <GenericWidget
                    node-alias="name_content"
                    graph-slug="digital_object_rdm_system"
                    :mode="EDIT"
                    :aliased-node-data="
                        digitalObjectResource?.aliased_data.name?.aliased_data
                            .name_content
                    "
                    class="widget-container column"
                />
                <GenericWidget
                    node-alias="statement_content"
                    graph-slug="digital_object_rdm_system"
                    :mode="EDIT"
                    :aliased-node-data="
                        digitalObjectResource?.aliased_data.statement
                            ?.aliased_data.statement_content
                    "
                    class="widget-container column"
                />
                <GenericWidget
                    node-alias="content"
                    graph-slug="digital_object_rdm_system"
                    :aliased-node-data="
                        digitalObjectResource?.aliased_data?.content
                            ?.aliased_data.content
                    "
                    :mode="EDIT"
                    :should-show-label="false"
                    class="widget-container column"
                />
            </Form>
        </div>
    </div>
</template>
<style scoped>
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

:deep(.p-fileupload-file-info) {
    flex-direction: row;
}

:deep(.p-fileupload-content) {
    padding: 0;
    margin-top: 1rem;
}
</style>
