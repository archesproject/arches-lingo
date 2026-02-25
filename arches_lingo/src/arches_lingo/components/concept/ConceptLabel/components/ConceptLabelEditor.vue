<script setup lang="ts">
import { inject, ref, useTemplateRef, watch } from "vue";

import { useRoute, useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import { Form } from "@primevue/forms";

import Skeleton from "primevue/skeleton";

import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import { createOrUpdateConcept } from "@/arches_lingo/utils.ts";

import {
    DEFAULT_ERROR_TOAST_LIFE,
    EDIT,
    ERROR,
} from "@/arches_lingo/constants.ts";

import type { Component, Ref } from "vue";
import type { FormSubmitEvent } from "@primevue/forms";
import type {
    AppellativeStatus,
    AppellativeStatusAliases,
    Label,
} from "@/arches_lingo/types.ts";

const props = defineProps<{
    tileData: AppellativeStatus | undefined;
    componentName: string;
    sectionTitle: string;
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId: string | undefined;
    tileId?: string;
}>();

const route = useRoute();
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

const refreshSchemeHierarchy = inject<() => void>("refreshSchemeHierarchy");
const commitTreeConcept =
    inject<
        (
            conceptId: string,
            labels: Label[],
            schemeId: string,
            parentId: string,
        ) => void
    >("commitTreeConcept");

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

        const updatedTileData: Partial<AppellativeStatusAliases> = {
            ...aliasedTileData,
            ...Object.fromEntries(
                Object.entries(formData).filter(
                    ([key]) => key in aliasedTileData,
                ),
            ),
        };

        const scheme = route.query.scheme as string;
        const parent = route.query.parent as string;

        const updatedTileId = await createOrUpdateConcept(
            updatedTileData,
            props.graphSlug,
            props.nodegroupAlias,
            scheme,
            parent,
            router,
            props.resourceInstanceId,
            props.tileId,
        );

        if (updatedTileId !== props.tileId) {
            openEditor!(props.componentName, updatedTileId);
        }

        refreshReportSection!(props.componentName);

        if (!props.resourceInstanceId) {
            // New concept — insert into tree locally instead of full refetch.
            const newConceptId = route.params.id as string;
            const labelValue =
                updatedTileData.appellative_status_ascribed_name_content
                    ?.display_value ??
                updatedTileData.appellative_status_ascribed_name_content
                    ?.node_value ??
                "";
            const languageId =
                updatedTileData.appellative_status_ascribed_name_language
                    ?.display_value ?? "";
            const valuetypeId =
                updatedTileData.appellative_status_ascribed_relation
                    ?.display_value ?? "preferred label";
            commitTreeConcept!(
                newConceptId,
                [
                    {
                        value:
                            typeof labelValue === "string"
                                ? labelValue
                                : String(labelValue),
                        language_id: languageId,
                        valuetype_id: valuetypeId,
                    },
                ],
                scheme,
                parent,
            );
        } else {
            // Existing concept — update tree labels locally.
            refreshSchemeHierarchy!();
        }
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
                        "Define the label type, status, language, and time span over which it was used.",
                    )
                }}
            </div>
        </div>

        <div class="form-container">
            <Form
                ref="form"
                @submit="save"
            >
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_ascribed_name_content"
                    :aliased-node-data="
                        props.tileData?.aliased_data
                            ?.appellative_status_ascribed_name_content
                    "
                    :mode="EDIT"
                    class="widget-container column"
                />
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_ascribed_relation"
                    :aliased-node-data="
                        props.tileData?.aliased_data
                            ?.appellative_status_ascribed_relation
                    "
                    :mode="EDIT"
                    class="widget-container column"
                />
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_ascribed_name_language"
                    :aliased-node-data="
                        props.tileData?.aliased_data
                            ?.appellative_status_ascribed_name_language
                    "
                    :mode="EDIT"
                    class="widget-container column"
                />
                <div class="widget-container">
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_timespan_begin_of_the_begin"
                        :aliased-node-data="
                            props.tileData?.aliased_data
                                ?.appellative_status_timespan_begin_of_the_begin
                        "
                        :mode="EDIT"
                    />
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_timespan_end_of_the_end"
                        :aliased-node-data="
                            props.tileData?.aliased_data
                                ?.appellative_status_timespan_end_of_the_end
                        "
                        :mode="EDIT"
                    />
                </div>
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_status"
                    :aliased-node-data="
                        props.tileData?.aliased_data?.appellative_status_status
                    "
                    :mode="EDIT"
                    class="widget-container column"
                />
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_data_assignment_actor"
                    :aliased-node-data="
                        props.tileData?.aliased_data
                            ?.appellative_status_data_assignment_actor
                    "
                    :mode="EDIT"
                    class="widget-container column"
                />
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_data_assignment_object_used"
                    :aliased-node-data="
                        props.tileData?.aliased_data
                            ?.appellative_status_data_assignment_object_used
                    "
                    :mode="EDIT"
                    class="widget-container column"
                />
            </Form>
        </div>
    </div>
</template>
