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
import type { AppellativeStatus } from "@/arches_lingo/types.ts";

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
const onSaveSettled = inject<() => void>("onSaveSettled");

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

        await refreshReportSection!(props.componentName);
        openEditor!(props.componentName, updatedTileId);
        refreshSchemeHierarchy!();
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to save data."),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isSaving.value = false;
        onSaveSettled?.();
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
                <div class="widget-container column">
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_ascribed_name_content"
                        :aliased-node-data="
                            props.tileData?.aliased_data
                                ?.appellative_status_ascribed_name_content ??
                            null
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_ascribed_relation"
                        :aliased-node-data="
                            props.tileData?.aliased_data
                                ?.appellative_status_ascribed_relation ?? null
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_ascribed_name_language"
                        :aliased-node-data="
                            props.tileData?.aliased_data
                                ?.appellative_status_ascribed_name_language ??
                            null
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container">
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_timespan_begin_of_the_begin"
                        :aliased-node-data="
                            props.tileData?.aliased_data
                                ?.appellative_status_timespan_begin_of_the_begin ??
                            null
                        "
                        :mode="EDIT"
                    />
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_timespan_end_of_the_end"
                        :aliased-node-data="
                            props.tileData?.aliased_data
                                ?.appellative_status_timespan_end_of_the_end ??
                            null
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_status"
                        :aliased-node-data="
                            props.tileData?.aliased_data
                                ?.appellative_status_status ?? null
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_data_assignment_actor"
                        :aliased-node-data="
                            props.tileData?.aliased_data
                                ?.appellative_status_data_assignment_actor ??
                            null
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_data_assignment_object_used"
                        :aliased-node-data="
                            props.tileData?.aliased_data
                                ?.appellative_status_data_assignment_object_used ??
                            null
                        "
                        :mode="EDIT"
                    />
                </div>
            </Form>
        </div>
    </div>
</template>
