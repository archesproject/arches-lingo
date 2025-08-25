<script setup lang="ts">
import { computed, inject, ref, useTemplateRef, watch } from "vue";

import { useRouter } from "vue-router";
import { Form } from "@primevue/forms";

import Skeleton from "primevue/skeleton";

import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import { createLingoResource, upsertLingoTile } from "@/arches_lingo/api.ts";
import { EDIT } from "@/arches_lingo/constants.ts";

import type { Component, Ref } from "vue";
import type { FormSubmitEvent } from "@primevue/forms";
import type { ConceptClassificationStatus } from "@/arches_lingo/types.ts";

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
const refreshSchemeHierarchy = inject<() => void>("refreshSchemeHierarchy");

const formRef = useTemplateRef("form");
const isSaving = ref(false);

// this is a workaround to make ResourceInstanceSelectWidget work
const computedValue = computed(() => {
    if (
        props.tileData?.aliased_data
            .classification_status_ascribed_classification?.node_value
    ) {
        return {
            resource_id:
                props.tileData.aliased_data
                    .classification_status_ascribed_classification.node_value,
        };
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
            const updatedConcept = await createLingoResource(
                {
                    aliased_data: {
                        [props.nodegroupAlias]: [updatedTileData],
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
                formData.classification_status_ascribed_classification
                    .resource_id == props.schemeId
            ) {
                nodegroupAlias = "top_concept_of";
                values = {
                    top_concept_of:
                        formData.classification_status_ascribed_classification,
                };
            } else {
                nodegroupAlias = props.nodegroupAlias;
                values = updatedTileData;
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
        refreshSchemeHierarchy!();
    } catch (error) {
        console.error(error);
    } finally {
        refreshReportSection!(props.componentName);
    }
}
</script>

<template>
    <Skeleton
        v-if="isSaving"
        style="width: 100%"
    />

    <div v-else>
        <h3>{{ props.sectionTitle }}</h3>

        <Form
            ref="form"
            @submit="save"
        >
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="classification_status_ascribed_classification"
                :aliased-node-data="computedValue"
                :mode="EDIT"
            />
        </Form>
    </div>
</template>
