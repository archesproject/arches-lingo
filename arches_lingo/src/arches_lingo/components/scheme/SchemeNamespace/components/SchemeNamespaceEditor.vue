<script setup lang="ts">
import { inject, ref, useTemplateRef, watch, type Component, type Ref } from "vue";
import { useRouter } from "vue-router";

import { Form } from "@primevue/forms";

import ProgressSpinner from "primevue/progressspinner";

import NonLocalizedStringWidget from "@/arches_component_lab/widgets/NonLocalizedStringWidget/NonLocalizedStringWidget.vue";

import { createScheme, upsertLingoTile } from "@/arches_lingo/api.ts";
import { EDIT } from "@/arches_lingo/constants.ts";

import type { FormSubmitEvent } from "@primevue/forms";
import type { SchemeNamespace } from "@/arches_lingo/types.ts";

const router = useRouter();

const props = defineProps<{
    tileData: SchemeNamespace | undefined;
    graphSlug: string;
    sectionTitle: string;
    resourceInstanceId: string | undefined;
    componentName: string;
    nodegroupAlias: string;
    tileId?: string;
}>();

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
        <NonLocalizedStringWidget
            node-alias="namespace_name"
            :graph-slug="props.graphSlug"
            :initial-value="props.tileData?.namespace_name"
            :mode="EDIT"
        />
    </Form>
</template>
