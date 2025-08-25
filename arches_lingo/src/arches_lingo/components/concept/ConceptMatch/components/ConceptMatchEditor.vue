<script setup lang="ts">
import { inject, ref, useTemplateRef, watch } from "vue";

import { useRouter } from "vue-router";
import { Form } from "@primevue/forms";

import Skeleton from "primevue/skeleton";

import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import { createLingoResource, upsertLingoTile } from "@/arches_lingo/api.ts";
import { EDIT } from "@/arches_lingo/constants.ts";

import type { Component, Ref } from "vue";
import type { FormSubmitEvent } from "@primevue/forms";
import type { ConceptMatchStatus } from "@/arches_lingo/types.ts";

const props = defineProps<{
    tileData: ConceptMatchStatus | undefined;
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

            updatedTileId = updatedConcept[props.nodegroupAlias][0].tileid;
        } else {
            const updatedConcept = await upsertLingoTile(
                props.graphSlug,
                props.nodegroupAlias,
                {
                    resourceinstance: props.resourceInstanceId,
                    aliased_data: { ...updatedTileData },
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
    <Skeleton
        v-show="isSaving"
        style="width: 100%"
    />

    <div v-show="!isSaving">
        <h3>{{ props.sectionTitle }}</h3>

        <Form
            ref="form"
            @submit="save"
        >
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="match_status_ascribed_comparate"
                :aliased-node-data="
                    props.tileData?.aliased_data.match_status_ascribed_comparate
                "
                :mode="EDIT"
            />
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="match_status_ascribed_relation"
                :aliased-node-data="
                    props.tileData?.aliased_data.match_status_ascribed_relation
                "
                :mode="EDIT"
            />
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="match_status_status"
                :aliased-node-data="
                    props.tileData?.aliased_data.match_status_status
                "
                :mode="EDIT"
            />
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="match_status_status_metatype"
                :aliased-node-data="
                    props.tileData?.aliased_data.match_status_status_metatype
                "
                :mode="EDIT"
            />
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="match_status_timespan_begin_of_the_begin"
                :aliased-node-data="
                    props.tileData?.aliased_data
                        .match_status_timespan_begin_of_the_begin
                "
                :mode="EDIT"
            />
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="match_status_timespan_end_of_the_end"
                :aliased-node-data="
                    props.tileData?.aliased_data
                        .match_status_timespan_end_of_the_end
                "
                :mode="EDIT"
            />
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="match_status_data_assignment_actor"
                :aliased-node-data="
                    props.tileData?.aliased_data
                        .match_status_data_assignment_actor
                "
                :mode="EDIT"
            />
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="match_status_data_assignment_object_used"
                :aliased-node-data="
                    props.tileData?.aliased_data
                        .match_status_data_assignment_object_used
                "
                :mode="EDIT"
            />
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="match_status_data_assignment_type"
                :aliased-node-data="
                    props.tileData?.aliased_data
                        .match_status_data_assignment_type
                "
                :mode="EDIT"
            />
        </Form>
    </div>
</template>
