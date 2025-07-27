<script setup lang="ts">
import { inject, ref, useTemplateRef, watch } from "vue";

import { useRoute, useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import { Form } from "@primevue/forms";

import Skeleton from "primevue/skeleton";

import DateWidget from "@/arches_component_lab/widgets/DateWidget/DateWidget.vue";
import NonLocalizedStringWidget from "@/arches_component_lab/widgets/NonLocalizedStringWidget/NonLocalizedStringWidget.vue";
import ReferenceSelectWidget from "@/arches_controlled_lists/widgets/ReferenceSelectWidget/ReferenceSelectWidget.vue";
import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

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

        const scheme = route.query.scheme as string;
        const parent = route.query.parent as string;

        const updatedTileId = await createOrUpdateConcept(
            formData,
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
                {{ $gettext("Define the label type, status, language, and time span over which it was used.") }}
            </div>
        </div>

        <div class="form-container">
            <Form
                ref="form"
                @submit="save"
            >
                <div class="widget-container column">
                    <NonLocalizedStringWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_ascribed_name_content"
                        :value="
                            props.tileData?.aliased_data
                                ?.appellative_status_ascribed_name_content
                                ?.interchange_value
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <ReferenceSelectWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_ascribed_relation"
                        :value="
                            props.tileData?.aliased_data
                                ?.appellative_status_ascribed_relation
                                ?.interchange_value
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <ReferenceSelectWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_ascribed_name_language"
                        :value="
                            props.tileData?.aliased_data
                                ?.appellative_status_ascribed_name_language
                                ?.interchange_value
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container">
                    <DateWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_timespan_begin_of_the_begin"
                        :value="
                            props.tileData?.aliased_data
                                ?.appellative_status_timespan_begin_of_the_begin
                                ?.interchange_value
                        "
                        :mode="EDIT"
                    />
                    <DateWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_timespan_end_of_the_end"
                        :value="
                            props.tileData?.aliased_data
                                ?.appellative_status_timespan_end_of_the_end
                                ?.interchange_value
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <ReferenceSelectWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_status"
                        :value="
                            props.tileData?.aliased_data?.appellative_status_status
                                ?.interchange_value
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <ResourceInstanceMultiSelectWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_data_assignment_actor"
                        :value="
                            props.tileData?.aliased_data
                                ?.appellative_status_data_assignment_actor
                                ?.interchange_value
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <ResourceInstanceMultiSelectWidget
                        :graph-slug="props.graphSlug"
                        node-alias="appellative_status_data_assignment_object_used"
                        :value="
                            props.tileData?.aliased_data
                                ?.appellative_status_data_assignment_object_used
                                ?.interchange_value
                        "
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

:deep(.p-treeselect) {
    border-radius: .125rem;
}

:deep(.p-multiselect) {
    border-radius: .125rem;
}

</style>