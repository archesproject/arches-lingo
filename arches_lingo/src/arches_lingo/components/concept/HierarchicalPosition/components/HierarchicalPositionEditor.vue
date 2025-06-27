<script setup lang="ts">
import { computed, inject, ref, useTemplateRef, watch } from "vue";

import { useRouter } from "vue-router";
import { Form } from "@primevue/forms";

import ProgressSpinner from "primevue/progressspinner";

import ResourceInstanceSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceSelectWidget/ResourceInstanceSelectWidget.vue";

import { createLingoResource, upsertLingoTile } from "@/arches_lingo/api.ts";
import { EDIT } from "@/arches_lingo/constants.ts";

import type { Component, Ref } from "vue";
import type { FormSubmitEvent } from "@primevue/forms";
import type { ConceptClassificationStatus } from "@/arches_lingo/types.ts";
import type { ResourceInstanceReference } from "@/arches_component_lab/widgets/types.ts";

const props = defineProps<{
    tileData: ConceptClassificationStatus | undefined;
    schemeId?: string;
    exclude?: boolean;
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
const isSaving = ref(false);

// this is a workaround to make ResourceInstanceSelectWidget work
const computedValue = computed(() => {
    if (
        props.tileData?.aliased_data
            .classification_status_ascribed_classification?.interchange_value
    ) {
        return {
            resource_id:
                props.tileData.aliased_data
                    .classification_status_ascribed_classification
                    .interchange_value,
        } as ResourceInstanceReference;
    }
    return null;
});

watch(
    () => formRef.value,
    (formComponent) => (componentEditorFormRef!.value = formComponent),
);

async function save(e: FormSubmitEvent) {
    isSaving.value = true;

    try {
        const formData = e.values;

        let updatedTileId;

        if (!props.resourceInstanceId) {
            const updatedConcept = await createLingoResource(
                {
                    aliased_data: {
                        [props.nodegroupAlias]: [formData],
                    },
                },
                props.graphSlug,
            );

            await router.push({
                name: props.graphSlug,
                params: { id: updatedConcept.resourceinstanceid },
            });
            updatedTileId =
                updatedConcept.aliased_data[props.nodegroupAlias][0].tileid;
        } else {
            let nodegroupAlias;
            let values;
            if (
                formData.classification_status_ascribed_classification[0]
                    .resourceId == props.schemeId
            ) {
                nodegroupAlias = "top_concept_of";
                values = {
                    top_concept_of:
                        formData.classification_status_ascribed_classification,
                };
            } else {
                nodegroupAlias = props.nodegroupAlias;
                values = formData;
            }

            const updatedConcept = await upsertLingoTile(
                props.graphSlug,
                nodegroupAlias,
                {
                    resourceinstance: props.resourceInstanceId,
                    aliased_data: { ...values },
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
    <ProgressSpinner
        v-if="isSaving"
        style="width: 100%"
    />

    <div v-else>
        <h3>{{ props.sectionTitle }}</h3>

        <Form
            ref="form"
            @submit="save"
        >
            <ResourceInstanceSelectWidget
                :graph-slug="props.graphSlug"
                node-alias="classification_status_ascribed_classification"
                :initial-value="computedValue"
                :mode="EDIT"
            />
        </Form>
    </div>
</template>
