<script setup lang="ts">
import { inject, ref, useTemplateRef, watch } from "vue";

import { useRoute, useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import { Form } from "@primevue/forms";

import ProgressSpinner from "primevue/progressspinner";

import DateWidget from "@/arches_component_lab/widgets/DateWidget/DateWidget.vue";
import NonLocalizedStringWidget from "@/arches_component_lab/widgets/NonLocalizedStringWidget/NonLocalizedStringWidget.vue";
import ReferenceSelectWidget from "@/arches_controlled_lists/widgets/ReferenceSelectWidget/ReferenceSelectWidget.vue";
import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

import { createLingoResource, upsertLingoTile } from "@/arches_lingo/api.ts";
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

const formRef = useTemplateRef("form");
const isSaving = ref(false);

watch(
    () => formRef.value,
    (formComponent) => (componentEditorFormRef!.value = formComponent),
);

async function save(e: FormSubmitEvent) {
    isSaving.value = true;

    try {
        const formData = Object.fromEntries(
            Object.entries(e.states).map(([key, state]) => [key, state.value]),
        );

        let updatedTileId;

        if (!props.resourceInstanceId) {
            const updatedConcept = await createLingoResource(
                {
                    aliased_data: {
                        [props.nodegroupAlias]: [formData],
                        part_of_scheme: {
                            "resourceId": route.query.scheme,
                        },
                        classification_status: [{
                            classification_status_ascribed_classification: {
                                "resourceId": route.query.parent,
                            }
                        }]
                    },
                },
                props.graphSlug,
            );

            await router.push({
                name: props.graphSlug,
                params: { id: updatedConcept.resourceinstanceid },
            });

            updatedTileId = updatedConcept.aliased_data[props.nodegroupAlias][0].tileid;
        } else {
            const updatedTile = await upsertLingoTile(
                props.graphSlug,
                props.nodegroupAlias,
                {
                    resourceinstance: props.resourceInstanceId,
                    aliased_data: { ...formData },
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
    <ProgressSpinner
        v-show="isSaving"
        style="width: 100%"
    />

    <div v-show="!isSaving">
        <h3>{{ props.sectionTitle }}</h3>

        <Form
            ref="form"
            @submit="save"
        >
            <NonLocalizedStringWidget
                :graph-slug="props.graphSlug"
                node-alias="appellative_status_ascribed_name_content"
                :initial-value="
                    props.tileData?.aliased_data
                        ?.appellative_status_ascribed_name_content
                "
                :mode="EDIT"
            />
            <DateWidget
                :graph-slug="props.graphSlug"
                node-alias="appellative_status_timespan_begin_of_the_begin"
                :initial-value="
                    props.tileData?.aliased_data
                        ?.appellative_status_timespan_begin_of_the_begin
                "
                :mode="EDIT"
            />
            <DateWidget
                :graph-slug="props.graphSlug"
                node-alias="appellative_status_timespan_end_of_the_end"
                :initial-value="
                    props.tileData?.aliased_data
                        ?.appellative_status_timespan_end_of_the_end
                "
                :mode="EDIT"
            />

            <ResourceInstanceMultiSelectWidget
                :graph-slug="props.graphSlug"
                node-alias="appellative_status_data_assignment_actor"
                :initial-value="
                    props.tileData?.aliased_data
                        ?.appellative_status_data_assignment_actor
                "
                :mode="EDIT"
            />
            <ResourceInstanceMultiSelectWidget
                :graph-slug="props.graphSlug"
                node-alias="appellative_status_data_assignment_object_used"
                :initial-value="
                    props.tileData?.aliased_data
                        ?.appellative_status_data_assignment_object_used
                "
                :mode="EDIT"
            />

            <ReferenceSelectWidget
                :graph-slug="props.graphSlug"
                node-alias="appellative_status_ascribed_name_language"
                :initial-value="
                    props.tileData?.aliased_data
                        ?.appellative_status_ascribed_name_language
                "
                :mode="EDIT"
            />
            <ReferenceSelectWidget
                :graph-slug="props.graphSlug"
                node-alias="appellative_status_ascribed_relation"
                :initial-value="
                    props.tileData?.aliased_data
                        ?.appellative_status_ascribed_relation
                "
                :mode="EDIT"
            />
            <ReferenceSelectWidget
                :graph-slug="props.graphSlug"
                node-alias="appellative_status_status"
                :initial-value="
                    props.tileData?.aliased_data?.appellative_status_status
                "
                :mode="EDIT"
            />
            <ReferenceSelectWidget
                :graph-slug="props.graphSlug"
                node-alias="appellative_status_status_metatype"
                :initial-value="
                    props.tileData?.aliased_data
                        ?.appellative_status_status_metatype
                "
                :mode="EDIT"
            />
            <ReferenceSelectWidget
                :graph-slug="props.graphSlug"
                node-alias="appellative_status_data_assignment_type"
                :initial-value="
                    props.tileData?.aliased_data
                        ?.appellative_status_data_assignment_type
                "
                :mode="EDIT"
            />
        </Form>
    </div>
</template>
