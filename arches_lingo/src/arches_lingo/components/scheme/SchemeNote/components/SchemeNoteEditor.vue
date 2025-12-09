<script setup lang="ts">
import { inject, ref, useTemplateRef, watch } from "vue";

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

import type { Component, Ref } from "vue";
import type { FormSubmitEvent } from "@primevue/forms";

import type { SchemeStatement } from "@/arches_lingo/types.ts";

const props = defineProps<{
    tileData: SchemeStatement | undefined;
    componentName: string;
    sectionTitle: string;
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId: string | undefined;
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

        const aliasedTileData = props.tileData?.aliased_data || {};

        const updatedTileData = {
            ...aliasedTileData,
            ...Object.fromEntries(
                Object.entries(formData).filter(
                    ([key]) => key in aliasedTileData,
                ),
            ),
        };

        let updatedTileId;

        if (!props.resourceInstanceId) {
            const updatedScheme = await createLingoResource(
                {
                    aliased_data: {
                        [props.nodegroupAlias]: [
                            { aliased_data: updatedTileData },
                        ],
                    },
                },
                props.graphSlug,
            );

            await router.push({
                name: props.graphSlug,
                params: { id: updatedScheme.resourceinstanceid },
            });

            updatedTileId =
                updatedScheme.aliased_data[props.nodegroupAlias][0].tileid;
        } else {
            const updatedTile = await upsertLingoTile(
                props.graphSlug,
                props.nodegroupAlias,
                {
                    resourceinstance: props.resourceInstanceId,
                    aliased_data: { ...updatedTileData },
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
        style="width: 100%; height: 100%"
    />

    <div v-show="!isSaving">
        <div class="form-header">
            <h3>{{ props.sectionTitle }}</h3>
            <div class="form-description">
                {{
                    $gettext(
                        "Provide notes and descriptions describing the scope and usage of this scheme.",
                    )
                }}
            </div>
        </div>
        <div class="form-container">
            <Form
                ref="form"
                @submit="save"
            >
                <div class="widget-container column">
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="statement_content"
                        :aliased-node-data="
                            props.tileData?.aliased_data?.statement_content
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="statement_type"
                        :aliased-node-data="
                            props.tileData?.aliased_data?.statement_type
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="statement_language"
                        :aliased-node-data="
                            props.tileData?.aliased_data?.statement_language
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="statement_data_assignment_actor"
                        :aliased-node-data="
                            props.tileData?.aliased_data
                                ?.statement_data_assignment_actor
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="statement_data_assignment_object_used"
                        :aliased-node-data="
                            props.tileData?.aliased_data
                                ?.statement_data_assignment_object_used
                        "
                        :mode="EDIT"
                    />
                </div>
            </Form>
        </div>
    </div>
</template>
