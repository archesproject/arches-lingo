<script setup lang="ts">
import { inject, useTemplateRef, watch } from "vue";

import { useRouter } from "vue-router";
import { Form } from "@primevue/forms";

import DateWidget from "@/arches_component_lab/widgets/DateWidget/DateWidget.vue";
import NonLocalizedStringWidget from "@/arches_component_lab/widgets/NonLocalizedStringWidget/NonLocalizedStringWidget.vue";
import ReferenceSelectWidget from "@/arches_controlled_lists/widgets/ReferenceSelectWidget/ReferenceSelectWidget.vue";
import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

import { createConcept, upsertLingoTile } from "@/arches_lingo/api.ts";
import { EDIT } from "@/arches_lingo/constants.ts";

import type { Component, Ref } from "vue";
import type { FormSubmitEvent } from "@primevue/forms";

import type { ConceptStatement } from "@/arches_lingo/types.ts";

const props = defineProps<{
    tileData: ConceptStatement | undefined;
    componentName: string;
    sectionTitle: string;
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId: string | undefined;
    tileId?: string;
}>();

const router = useRouter();

const componentEditorFormRef = inject<Ref<Component | null>>(
    "componentEditorFormRef",
);

const openEditor =
    inject<(componentName: string, tileid?: string) => void>("openEditor");
const refreshReportSection = inject<(componentName: string) => void>(
    "refreshReportSection",
);

const formRef = useTemplateRef("form");
watch(
    () => formRef.value,
    (formComponent) => (componentEditorFormRef!.value = formComponent),
);

async function save(e: FormSubmitEvent) {
    try {
        const formData = Object.fromEntries(
            Object.entries(e.states).map(([key, state]) => [key, state.value]),
        );

        let updatedTileId;

        if (!props.resourceInstanceId) {
            const updatedConcept = await createConcept({
                [props.nodegroupAlias]: [formData],
            });

            await router.push({
                name: props.graphSlug,
                params: { id: updatedConcept.resourceinstanceid },
            });

            updatedTileId = updatedConcept[props.nodegroupAlias][0].tileid;
        } else {
            const updatedConcept = await upsertLingoTile(
                props.graphSlug,
                props.nodegroupAlias,
                {
                    resourceinstance: props.resourceInstanceId,
                    ...formData,
                    tileid: props.tileId,
                },
            );

            updatedTileId = updatedConcept.tileid;
        }

        openEditor!(props.componentName, updatedTileId);
    } catch (error) {
        console.error(error);
    } finally {
        refreshReportSection!(props.componentName);
    }
}
</script>

<template>
    <h3>{{ props.sectionTitle }}</h3>

    <Form
        ref="form"
        @submit="save"
    >
        <NonLocalizedStringWidget
            :graph-slug="props.graphSlug"
            node-alias="statement_content"
            :initial-value="props.tileData?.statement_content"
            :mode="EDIT"
        />
        <ReferenceSelectWidget
            :graph-slug="props.graphSlug"
            node-alias="statement_language"
            :initial-value="props.tileData?.statement_language"
            :mode="EDIT"
        />
        <ReferenceSelectWidget
            :graph-slug="props.graphSlug"
            node-alias="statement_type"
            :initial-value="props.tileData?.statement_type"
            :mode="EDIT"
        />
        <ReferenceSelectWidget
            :graph-slug="props.graphSlug"
            node-alias="statement_type_metatype"
            :initial-value="props.tileData?.statement_type_metatype"
            :mode="EDIT"
        />
        <DateWidget
            :graph-slug="props.graphSlug"
            node-alias="statement_data_assignment_timespan_begin_of_the_begin"
            :initial-value="
                props.tileData
                    ?.statement_data_assignment_timespan_begin_of_the_begin
            "
            :mode="EDIT"
        />
        <DateWidget
            :graph-slug="props.graphSlug"
            node-alias="statement_data_assignment_timespan_end_of_the_end"
            :initial-value="
                props.tileData
                    ?.statement_data_assignment_timespan_end_of_the_end
            "
            :mode="EDIT"
        />
        <ResourceInstanceMultiSelectWidget
            :graph-slug="props.graphSlug"
            node-alias="statement_data_assignment_actor"
            :initial-value="props.tileData?.statement_data_assignment_actor"
            :mode="EDIT"
        />
        <ResourceInstanceMultiSelectWidget
            :graph-slug="props.graphSlug"
            node-alias="statement_data_assignment_object_used"
            :initial-value="
                props.tileData?.statement_data_assignment_object_used
            "
            :mode="EDIT"
        />
        <ReferenceSelectWidget
            :graph-slug="props.graphSlug"
            node-alias="statement_data_assignment_type"
            :initial-value="props.tileData?.statement_data_assignment_type"
            :mode="EDIT"
        />
    </Form>
</template>
