<script setup lang="ts">
import { inject, ref, useTemplateRef, watch, type Component, type Ref } from "vue";
import { useRouter } from "vue-router";

import { Form } from "@primevue/forms";

import ProgressSpinner from "primevue/progressspinner";

import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

import { createScheme, upsertLingoTile } from "@/arches_lingo/api.ts";
import { EDIT } from "@/arches_lingo/constants.ts";

import type { FormSubmitEvent } from "@primevue/forms";
import type { SchemeCreation } from "@/arches_lingo/types.ts";

const props = defineProps<{
    tileData: SchemeCreation | undefined;
    graphSlug: string;
    sectionTitle: string;
    resourceInstanceId: string | undefined;
    componentName: string;
    nodegroupAlias: string;
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

const isSaving = ref(false);
const formRef = useTemplateRef("form");
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
            const updatedScheme = await createScheme({
                [props.nodegroupAlias]: formData,
            });

            await router.push({
                name: props.graphSlug,
                params: { id: updatedScheme.resourceinstanceid },
            });

            updatedTileId = updatedScheme[props.nodegroupAlias][0].tileid;
        } else {
            const updatedScheme = await upsertLingoTile(
                props.graphSlug,
                props.nodegroupAlias,
                {
                    resourceinstance: props.resourceInstanceId,
                    ...formData,
                    tileid: props.tileId,
                },
            );

            updatedTileId = updatedScheme.tileid;
        }

        openEditor!(props.componentName, updatedTileId);
    } catch (error) {
        console.error(error);
    } finally {
        refreshReportSection!(props.componentName);
        isSaving.value = false;
        console.log("done saving");
    }
}
</script>

<template>
    <h3>{{ props.sectionTitle }}</h3>

    <ProgressSpinner
        v-if="isSaving"
        style="width: 100%"
    />
    <Form
        v-else
        ref="form"
        @submit="save"
    >
        <ResourceInstanceMultiSelectWidget
            graph-slug="scheme"
            node-alias="creation_sources"
            :initial-value="props.tileData?.creation_sources"
            :mode="EDIT"
        />
    </Form>
</template>
