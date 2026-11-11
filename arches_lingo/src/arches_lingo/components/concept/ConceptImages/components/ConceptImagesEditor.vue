<script setup lang="ts">
import { inject, nextTick, onMounted, ref, useTemplateRef, watch } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "openvue/usetoast";

import { Form } from "@openvue/forms";

import Skeleton from "openvue/skeleton";

import GenericWidget from "@/arches_vue_components/generics/GenericWidget/GenericWidget.vue";
import { DIGITAL_OBJECT_GRAPH_SLUG } from "@/arches_lingo/components/concept/ConceptImages/components/constants.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    EDIT,
    ERROR,
    MULTILINE_RENDER_CONTEXT,
} from "@/arches_lingo/constants.ts";

import {
    createFormDataForFileUpload,
    addDigitalObjectToConceptImageCollection,
    createDigitalObject,
} from "@/arches_lingo/components/concept/ConceptImages/components/utils.ts";

import { useConceptImagesEditorStore } from "@/arches_lingo/stores/useConceptImagesEditorStore.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { useWidgetConfigStore } from "@/arches_vue_components/stores/useWidgetConfigStore.ts";
import { setLocalizedValue } from "@/arches_vue_components/datatypes/file-list/utils.ts";
import { storeToRefs } from "pinia";

import {
    fetchLingoResource,
    updateLingoResource,
    updateLingoResourceFromForm,
} from "@/arches_lingo/api.ts";

import type { Component, Ref } from "vue";
import type { FormSubmitEvent } from "@openvue/forms";
import type { Language } from "@/arches_vue_components/types.ts";
import type { NonLocalizedTextAliasedNodeData } from "@/arches_vue_components/datatypes/non-localized-text/types.ts";
import type {
    FileListAliasedNodeData,
    FileListCardXNodeXWidgetData,
    FileReference,
} from "@/arches_vue_components/datatypes/file-list/types.ts";

import type {
    ConceptImages,
    DigitalObjectInstance,
    DigitalObjectInstanceAliases,
} from "@/arches_lingo/types.ts";

type PossiblyNewFile = FileReference & {
    file?: File;
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
const languageStore = useLanguageStore();

const digitalObjectResource = ref<DigitalObjectInstance>();
const digitalObjectLoaded = ref(false);
const contentCardXNodeXWidgetData = ref<FileListCardXNodeXWidgetData>();

const componentEditorFormRef = inject<Ref<Component | null>>(
    "componentEditorFormRef",
);
const openEditor =
    inject<(componentName: string, tileid?: string) => void>("openEditor");
const closeEditor = inject<() => void>("closeEditor");
const refreshReportSection = inject<(componentName: string) => void>(
    "refreshReportSection",
);
const onSaveSettled = inject<() => void>("onSaveSettled");

const formRef = useTemplateRef("form");
const isLoading = ref(true);
const { targetDigitalObjectResourceInstanceId } = storeToRefs(
    useConceptImagesEditorStore(),
);

onMounted(() => {
    getDigitalObjectInstance(targetDigitalObjectResourceInstanceId.value);
    getContentCardXNodeXWidgetData();
});

// Lingo collects title and description in its own Title and Description
// fields and copies them into the file record on save, so hide them in the
// file widget the way a card hides a node: flip the field's visible bit.
async function getContentCardXNodeXWidgetData() {
    try {
        const cardXNodeXWidgetData =
            (await useWidgetConfigStore().fetchWidgetConfig(
                DIGITAL_OBJECT_GRAPH_SLUG,
                "content",
            )) as FileListCardXNodeXWidgetData;
        // The store shares one cached object, so copy rather than mutate it.
        contentCardXNodeXWidgetData.value = {
            ...cardXNodeXWidgetData,
            config: {
                ...cardXNodeXWidgetData.config,
                metadataFields: {
                    ...cardXNodeXWidgetData.config.metadataFields,
                    title: { visible: false },
                    description: { visible: false },
                },
            },
        };
    } catch (error) {
        console.error(error);
    }
}

watch(
    () => formRef.value,
    (formComponent) => (componentEditorFormRef!.value = formComponent),
);

async function getDigitalObjectInstance(resourceInstanceId?: string) {
    try {
        if (resourceInstanceId === undefined) {
            digitalObjectResource.value = undefined;
        } else {
            digitalObjectResource.value = await fetchLingoResource(
                "digital_object_system",
                resourceInstanceId,
            );
        }
        digitalObjectLoaded.value = true;
        isLoading.value = false;
    } catch (error) {
        console.error(error);
    }
}

function getTileLanguage(
    tileAliasedData: object | undefined,
    languageNodeAlias: string,
): Language {
    const languageNode = (
        tileAliasedData as
            | Record<string, { node_value?: unknown } | undefined>
            | undefined
    )?.[languageNodeAlias];
    return (
        languageStore.availableLanguages.find(
            (language) => language.code === languageNode?.node_value,
        ) ?? languageStore.selectedLanguage
    );
}

function getNonLocalizedText(aliasedNodeData: object | undefined): string {
    return (
        (aliasedNodeData as NonLocalizedTextAliasedNodeData | undefined)
            ?.node_value ?? ""
    );
}

function withRecordTitleAndDescription(
    file: PossiblyNewFile,
    digitalObjectInstanceAliases: DigitalObjectInstanceAliases,
): PossiblyNewFile {
    const nameAliasedData = digitalObjectInstanceAliases.name?.aliased_data;
    const statementAliasedData =
        digitalObjectInstanceAliases.statement?.aliased_data;

    return {
        ...file,
        title: setLocalizedValue(
            file.title,
            getTileLanguage(nameAliasedData, "name_language"),
            getNonLocalizedText(nameAliasedData?.name_content),
        ),
        description: setLocalizedValue(
            file.description,
            getTileLanguage(statementAliasedData, "statement_language"),
            getNonLocalizedText(statementAliasedData?.statement_content),
        ),
    };
}

async function save(e: FormSubmitEvent) {
    isLoading.value = true;

    try {
        const submittedFormData = e.values;
        const digitalObjectInstanceAliases: DigitalObjectInstanceAliases =
            digitalObjectResource.value?.aliased_data ?? {};

        if (submittedFormData.name_content) {
            digitalObjectInstanceAliases.name = {
                ...digitalObjectInstanceAliases.name,
                aliased_data: { name_content: submittedFormData.name_content },
            };
        }
        if (submittedFormData.statement_content) {
            digitalObjectInstanceAliases.statement = {
                ...digitalObjectInstanceAliases.statement,
                aliased_data: {
                    statement_content: submittedFormData.statement_content,
                },
            };
        }

        const submittedContentFiles =
            (
                submittedFormData.content as {
                    node_value: PossiblyNewFile[] | null;
                }
            )?.node_value ?? null;
        const contentFiles =
            submittedContentFiles?.map((file) =>
                withRecordTitleAndDescription(
                    file,
                    digitalObjectInstanceAliases,
                ),
            ) ?? null;

        // files do not respect json.stringify
        const fileJsonObjects = (contentFiles ?? []).map((file) => {
            if (!file.file) {
                return file;
            }
            return {
                name: file.name.replace(/ /g, "_"),
                lastModified: file.lastModified,
                size: file.size,
                type: file.type,
                url: null,
                file_id: null,
                content: URL.createObjectURL(file.file),
                altText: file.altText,
                title: file.title,
                description: file.description,
                attribution: file.attribution,
            };
        });

        digitalObjectInstanceAliases.content = {
            ...digitalObjectInstanceAliases.content,
            aliased_data: {
                content: {
                    node_value: fileJsonObjects,
                } as unknown as FileListAliasedNodeData,
            },
        };

        const hasNewFiles = (contentFiles ?? []).some(
            (file) => file.file instanceof File,
        );
        if (hasNewFiles) {
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
                { ...submittedFormData, content: contentFiles },
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
                await addDigitalObjectToConceptImageCollection(
                    digitalObject,
                    props.graphSlug,
                    props.nodegroupAlias,
                    props.resourceInstanceId,
                );
            }
        }

        refreshReportSection!(props.componentName);

        nextTick(() => {
            targetDigitalObjectResourceInstanceId.value =
                digitalObjectResource.value?.resourceinstanceid;
            getDigitalObjectInstance(
                targetDigitalObjectResourceInstanceId.value,
            );
        });

        closeEditor!();
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to save data."),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
        onSaveSettled?.();
    }
}

function resetForm() {
    targetDigitalObjectResourceInstanceId.value =
        digitalObjectResource?.value?.resourceinstanceid;
    openEditor!(props.componentName);
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
                <div class="widget-container column">
                    <GenericWidget
                        node-alias="name_content"
                        graph-slug="digital_object_system"
                        :mode="EDIT"
                        :aliased-node-data="
                            digitalObjectResource?.aliased_data.name
                                ?.aliased_data.name_content ?? null
                        "
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        node-alias="statement_content"
                        graph-slug="digital_object_system"
                        :mode="EDIT"
                        :aliased-node-data="
                            digitalObjectResource?.aliased_data.statement
                                ?.aliased_data.statement_content ?? null
                        "
                        :render-context="MULTILINE_RENDER_CONTEXT"
                    />
                </div>
                <div
                    v-if="contentCardXNodeXWidgetData"
                    class="widget-container column"
                >
                    <GenericWidget
                        node-alias="content"
                        graph-slug="digital_object_system"
                        :card-x-node-x-widget-data="contentCardXNodeXWidgetData"
                        :aliased-node-data="
                            digitalObjectResource?.aliased_data?.content
                                ?.aliased_data.content ?? null
                        "
                        :mode="EDIT"
                        :should-show-label="false"
                        :should-show-metadata-language-select="true"
                    />
                </div>
            </Form>
        </div>
    </div>
</template>
<style scoped>
:deep(.p-fileupload-advanced) {
    border: none;
}

:deep(.file-list) {
    display: flex;
    gap: 1rem;
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
