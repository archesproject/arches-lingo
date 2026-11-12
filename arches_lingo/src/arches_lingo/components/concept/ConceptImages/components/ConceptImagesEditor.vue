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
// Lingo 1.2 only: on 1.3, render `content` with GenericWidget and import the
// file-list utils and types from @/arches_vue_components.
import FileListMetadataWidget from "@/arches_lingo/components/widgets/FileListMetadataWidget/FileListMetadataWidget.vue";
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
import { setLocalizedValue } from "@/arches_lingo/components/widgets/FileListMetadataWidget/utils.ts";
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
import type { NonLocalizedTextAliasedNodeData } from "@/arches_vue_components/datatypes/non-localized-text/types.ts";
import type {
    FileListAliasedNodeData,
    FileListCardXNodeXWidgetData,
    FileReference,
} from "@/arches_lingo/components/widgets/FileListMetadataWidget/types.ts";

import type {
    ConceptImages,
    DigitalObjectContentAliases,
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
// One language for the whole digital object: the file widget's language
// picker sets it, and save() writes it to name_language and
// statement_language and files title and description under it.
const recordLanguageCode = ref<string>();

const recordLanguage = computed<Language>(
    () =>
        languageStore.availableLanguages.find(
            (language) => language.code === recordLanguageCode.value,
        ) ?? languageStore.selectedLanguage,
);

// Lingo's types use 2.0.x's file-list types, where metadata is a string;
// the stored value is localized, as the backport widget types it.
const contentAliasedNodeData = computed(
    () =>
        (digitalObjectResource.value?.aliased_data?.content?.aliased_data
            .content ?? null) as unknown as FileListAliasedNodeData | null,
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
    getContentCardXNodeXWidgetData();
});

// Lingo collects title and description in its own Title and Description
// fields and copies them into the file record on save, so hide them in the
// file widget the way a card hides a node: flip the field's visible bit.
// Flip the language picker's bit on, so editors can set the record language.
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
                metadataLanguageSelect: { visible: true },
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
        recordLanguageCode.value = getInitialRecordLanguageCode(
            digitalObjectResource.value?.aliased_data,
        );
        digitalObjectLoaded.value = true;
        isLoading.value = false;
    } catch (error) {
        console.error(error);
    }
}

// Lingo types the *_language nodes loosely (statement_language as a
// reference), but they are core `language` nodes holding a language code.
function getTileLanguageCode(
    tileAliasedData: object | undefined,
    languageNodeAlias: string,
): string | undefined {
    const languageNode = (
        tileAliasedData as
            | Record<string, { node_value?: unknown } | undefined>
            | undefined
    )?.[languageNodeAlias];
    const languageCode = languageNode?.node_value;
    return typeof languageCode === "string" && languageCode
        ? languageCode
        : undefined;
}

function getInitialRecordLanguageCode(
    digitalObjectInstanceAliases: DigitalObjectInstanceAliases | undefined,
): string {
    return (
        getTileLanguageCode(
            digitalObjectInstanceAliases?.name?.aliased_data,
            "name_language",
        ) ??
        getTileLanguageCode(
            digitalObjectInstanceAliases?.statement?.aliased_data,
            "statement_language",
        ) ??
        languageStore.selectedLanguage.code
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
            recordLanguage.value,
            getNonLocalizedText(nameAliasedData?.name_content),
        ),
        description: setLocalizedValue(
            file.description,
            recordLanguage.value,
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
        const recordLanguageAliasedNodeData = buildLanguageAliasedNodeData(
            recordLanguage.value.code,
            languageStore.availableLanguages,
        );

        if (submittedFormData.name_content) {
            digitalObjectInstanceAliases.name = {
                ...digitalObjectInstanceAliases.name,
                aliased_data: {
                    name_content: submittedFormData.name_content,
                    name_language: recordLanguageAliasedNodeData,
                },
            } as DigitalObjectInstanceAliases["name"];
        }
        if (submittedFormData.statement_content) {
            digitalObjectInstanceAliases.statement = {
                ...digitalObjectInstanceAliases.statement,
                aliased_data: {
                    statement_content: submittedFormData.statement_content,
                    statement_language: recordLanguageAliasedNodeData,
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
                } as unknown as DigitalObjectContentAliases["content"],
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
                    <FileListMetadataWidget
                        node-alias="content"
                        :card-x-node-x-widget-data="contentCardXNodeXWidgetData"
                        :aliased-node-data="contentAliasedNodeData"
                        :metadata-language-code="recordLanguageCode"
                        @update:metadata-language-code="
                            (languageCode: string) =>
                                (recordLanguageCode = languageCode)
                        "
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
