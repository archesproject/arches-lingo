<script setup lang="ts">
import {
    computed,
    inject,
    nextTick,
    onMounted,
    ref,
    useTemplateRef,
    watch,
} from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import { Form } from "@primevue/forms";

import Skeleton from "primevue/skeleton";

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
import { setLocalizedValue } from "@/arches_vue_components/datatypes/file-list/utils.ts";
import { buildLanguageAliasedNodeData } from "@/arches_vue_components/datatypes/language/utils.ts";
import { storeToRefs } from "pinia";

import {
    fetchLingoResource,
    updateLingoResource,
    updateLingoResourceFromForm,
} from "@/arches_lingo/api.ts";

import type { Component, Ref } from "vue";
import type { FormSubmitEvent } from "@primevue/forms";
import type { Language } from "@/arches_vue_components/types.ts";
import type { LanguageAliasedNodeData } from "@/arches_vue_components/datatypes/language/types.ts";
import type { NonLocalizedTextAliasedNodeData } from "@/arches_vue_components/datatypes/non-localized-text/types.ts";
import type {
    FileListAliasedNodeData,
    FileMetadataField,
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

const HIDDEN_FILE_METADATA_FIELDS: FileMetadataField[] = [
    "title",
    "description",
];

const initialNameLanguage = computed(() =>
    getLanguageAliasedNodeData(
        digitalObjectResource.value?.aliased_data.name?.aliased_data
            .name_language,
    ),
);
const initialStatementLanguage = computed(() =>
    getLanguageAliasedNodeData(
        digitalObjectResource.value?.aliased_data.statement?.aliased_data
            .statement_language,
    ),
);

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
});

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

function getLanguageAliasedNodeData(
    aliasedNodeData: object | undefined,
): LanguageAliasedNodeData {
    const languageCode =
        (aliasedNodeData as LanguageAliasedNodeData | undefined)?.node_value ||
        languageStore.selectedLanguage.code;
    return buildLanguageAliasedNodeData(
        languageCode,
        languageStore.availableLanguages,
    );
}

function findLanguage(
    languageAliasedNodeData: LanguageAliasedNodeData,
): Language {
    return (
        languageStore.availableLanguages.find(
            (language) => language.code === languageAliasedNodeData.node_value,
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
    nameLanguage: Language,
    statementLanguage: Language,
): PossiblyNewFile {
    const nameAliasedData = digitalObjectInstanceAliases.name?.aliased_data;
    const statementAliasedData =
        digitalObjectInstanceAliases.statement?.aliased_data;

    return {
        ...file,
        title: setLocalizedValue(
            file.title,
            nameLanguage,
            getNonLocalizedText(nameAliasedData?.name_content),
        ),
        description: setLocalizedValue(
            file.description,
            statementLanguage,
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
        const nameLanguageAliasedNodeData = getLanguageAliasedNodeData(
            submittedFormData.name_language,
        );
        const statementLanguageAliasedNodeData = getLanguageAliasedNodeData(
            submittedFormData.statement_language,
        );

        if (submittedFormData.name_content) {
            digitalObjectInstanceAliases.name = {
                ...digitalObjectInstanceAliases.name,
                aliased_data: {
                    name_content: submittedFormData.name_content,
                    name_language: nameLanguageAliasedNodeData,
                },
            } as DigitalObjectInstanceAliases["name"];
        }
        if (submittedFormData.statement_content) {
            digitalObjectInstanceAliases.statement = {
                ...digitalObjectInstanceAliases.statement,
                aliased_data: {
                    statement_content: submittedFormData.statement_content,
                    statement_language: statementLanguageAliasedNodeData,
                },
            } as unknown as DigitalObjectInstanceAliases["statement"];
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
                    findLanguage(nameLanguageAliasedNodeData),
                    findLanguage(statementLanguageAliasedNodeData),
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
                    <GenericWidget
                        node-alias="name_language"
                        graph-slug="digital_object_system"
                        :mode="EDIT"
                        :aliased-node-data="initialNameLanguage"
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
                    <GenericWidget
                        node-alias="statement_language"
                        graph-slug="digital_object_system"
                        :mode="EDIT"
                        :aliased-node-data="initialStatementLanguage"
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        node-alias="content"
                        graph-slug="digital_object_system"
                        :aliased-node-data="
                            digitalObjectResource?.aliased_data?.content
                                ?.aliased_data.content ?? null
                        "
                        :mode="EDIT"
                        :should-show-label="false"
                        :hidden-metadata-fields="HIDDEN_FILE_METADATA_FIELDS"
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
