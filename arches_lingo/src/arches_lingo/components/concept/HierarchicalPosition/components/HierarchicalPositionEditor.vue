<script setup lang="ts">
import { inject, ref, useTemplateRef, watch } from "vue";

import { useRouter } from "vue-router";
import Button from "primevue/button";
import { Form } from "@primevue/forms";

import ConceptResourceSelectWidget from "@/arches_lingo/components/widgets/ConceptResourceSelectWidget/ConceptResourceSelectWidget.vue";

import { createLingoResource, upsertLingoTile } from "@/arches_lingo/api.ts";
import { EDIT } from "@/arches_lingo/constants.ts";

import type { Component, Ref } from "vue";
import type { FormSubmitEvent } from "@primevue/forms";
import type { ConceptClassificationStatus } from "@/arches_lingo/types.ts";

const props = defineProps<{
    tileData: ConceptClassificationStatus | undefined;
    scheme?: string;
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
            if (Object.values(formData)[0][0].resourceId == props.scheme) {
                nodegroupAlias = "top_concept_of";
                values = { "top_concept_of": Object.values(formData)[0] };
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
        v-show="isSaving"
        style="width: 100%"
    />

    <div v-show="!isSaving">
        <h3>{{ props.sectionTitle }}</h3>

        <Form
            ref="form"
            @submit="save"
        >
            <ConceptResourceSelectWidget
                :graph-slug="props.graphSlug"
                node-alias="classification_status_ascribed_classification"
                :scheme="props.scheme"
                :exclude="props.exclude"
                :initial-value="
                    props.tileData?.aliased_data
                        .classification_status_ascribed_classification
                "
                :mode="EDIT"
            />
        </Form>
    </div>
</template>
