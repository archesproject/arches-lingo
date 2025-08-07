<script setup lang="ts">
import {
    inject,
    ref,
    useTemplateRef,
    watch,
    type Component,
    type Ref,
} from "vue";

import { useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import { Form } from "@primevue/forms";

import Skeleton from "primevue/skeleton";

import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import { createLingoResource, upsertLingoTile } from "@/arches_lingo/api.ts";

import {
    DEFAULT_ERROR_TOAST_LIFE,
    EDIT,
    ERROR,
} from "@/arches_lingo/constants.ts";

import type { FormSubmitEvent } from "@primevue/forms";
import type { SchemeRights } from "@/arches_lingo/types";

const props = defineProps<{
    tileData: SchemeRights | undefined;
    graphSlug: string;
    sectionTitle: string;
    resourceInstanceId: string | undefined;
    componentName: string;
    nodegroupAlias: string;
    tileId?: string;
}>();

const router = useRouter();
const toast = useToast();
const { $gettext } = useGettext();

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

watch(
    () => formRef.value,
    (formComponent) => (componentEditorFormRef!.value = formComponent),
);

async function save(e: FormSubmitEvent) {
    isSaving.value = true;

    try {
        const formData = e.values;

        // TODO: in future versions hit an API for expected shape &&
        // recursively map the form data to the expected shape
        const expectedTileShape = {
            right_holder: formData.right_holder,
            right_type: formData.right_type,
            right_statement: {
                aliased_data: {
                    right_statement_content: formData.right_statement_content,
                    right_statement_language: formData.right_statement_language,
                    right_statement_type: formData.right_statement_type,
                    right_statement_type_metatype:
                        formData.right_statement_type_metatype,
                },
            },
        };

        let updatedTileId;

        if (!props.resourceInstanceId) {
            const updatedScheme = await createLingoResource(
                {
                    aliased_data: {
                        [props.nodegroupAlias]: {
                            aliased_data: expectedTileShape,
                        },
                    },
                },
                props.graphSlug,
            );

            await router.push({
                name: props.graphSlug,
                params: { id: updatedScheme.resourceinstanceid },
            });

            updatedTileId =
                updatedScheme.aliased_data[props.nodegroupAlias].tileid;
        } else {
            if (props.tileData?.aliased_data.right_statement?.tileid) {
                (
                    expectedTileShape.right_statement as Record<string, unknown>
                ).tileid = props.tileData.aliased_data.right_statement.tileid;
            }

            const updatedTile = await upsertLingoTile(
                props.graphSlug,
                props.nodegroupAlias,
                {
                    resourceinstance: props.resourceInstanceId,
                    aliased_data: { ...expectedTileShape },
                    tileid: props.tileId,
                },
            );

            updatedTileId = updatedTile.tileid;
        }

        if (updatedTileId !== props.tileId) {
            openEditor!(props.componentName, updatedTileId);
        }

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
                {{ $gettext("Define the rights or license under which this scheme is managed.") }}
            </div>
        </div>
        <div class="form-container">
            <Form
                ref="form"
                @submit="save"
            >
                <div class="widget-container column">
                    <GenericWidget
                        node-alias="right_statement_content"
                        :graph-slug="props.graphSlug"
                        :aliased-node-data="
                            props.tileData?.aliased_data.right_statement?.aliased_data
                                .right_statement_content
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        node-alias="right_statement_type"
                        :graph-slug="props.graphSlug"
                        :aliased-node-data="
                            props.tileData?.aliased_data.right_statement?.aliased_data
                                .right_statement_type
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        node-alias="right_statement_language"
                        :graph-slug="props.graphSlug"
                        :aliased-node-data="
                            props.tileData?.aliased_data.right_statement?.aliased_data
                                .right_statement_language
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        node-alias="right_holder"
                        :graph-slug="props.graphSlug"
                        :aliased-node-data="props.tileData?.aliased_data.right_holder"
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        node-alias="right_type"
                        :graph-slug="props.graphSlug"
                        :aliased-node-data="props.tileData?.aliased_data.right_type"
                        :mode="EDIT"
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
    background: var(--p-editor-form-background);
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

</style>