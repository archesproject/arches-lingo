<script setup lang="ts">
import { inject, ref, useTemplateRef, watch } from "vue";

import { useRouter, useRoute } from "vue-router";
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
        <h3>{{ props.sectionTitle }}</h3>

        <Form
            ref="form"
            @submit="save"
        >
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="statement_content"
                :value="
                    props.tileData?.aliased_data.statement_content
                        ?.interchange_value
                "
                :mode="EDIT"
            />
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="statement_type"
                :value="
                    props.tileData?.aliased_data.statement_type
                        ?.interchange_value
                "
                :mode="EDIT"
            />
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="statement_language"
                :value="
                    props.tileData?.aliased_data.statement_language
                        ?.interchange_value
                "
                :mode="EDIT"
            />
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="statement_data_assignment_timespan_begin_of_the_begin"
                :value="
                    props.tileData?.aliased_data
                        .statement_data_assignment_timespan_begin_of_the_begin
                        ?.interchange_value
                "
                :mode="EDIT"
            />
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="statement_data_assignment_timespan_end_of_the_end"
                :value="
                    props.tileData?.aliased_data
                        .statement_data_assignment_timespan_end_of_the_end
                        ?.interchange_value
                "
                :mode="EDIT"
            />
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="statement_data_assignment_actor"
                :value="
                    props.tileData?.aliased_data.statement_data_assignment_actor
                        ?.interchange_value
                "
                :mode="EDIT"
            />
            <GenericWidget
                :graph-slug="props.graphSlug"
                node-alias="statement_data_assignment_object_used"
                :value="
                    props.tileData?.aliased_data
                        .statement_data_assignment_object_used
                        ?.interchange_value
                "
                :mode="EDIT"
            />
        </Form>
    </div>
</template>
