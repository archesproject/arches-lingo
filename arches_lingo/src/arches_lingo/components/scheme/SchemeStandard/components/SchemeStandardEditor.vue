<script setup lang="ts">
import {
    inject,
    ref,
    useTemplateRef,
    watch,
    type Component,
    type Ref,
} from "vue";
import { useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import { Form } from "@primevue/forms";

import ProgressSpinner from "primevue/progressspinner";

import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

import { createLingoResource, upsertLingoTile } from "@/arches_lingo/api.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    EDIT,
    ERROR,
} from "@/arches_lingo/constants.ts";

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
            const updatedScheme = await createLingoResource(
                {
                    [props.nodegroupAlias]: [formData],
                },
                props.graphSlug,
            );

            await router.push({
                name: props.graphSlug,
                params: { id: updatedScheme.resourceinstanceid },
            });

            updatedTileId = updatedScheme[props.nodegroupAlias][0].tileid;
            openEditor!(props.componentName, updatedTileId);
        } else {
            await upsertLingoTile(props.graphSlug, props.nodegroupAlias, {
                resourceinstance: props.resourceInstanceId,
                ...formData,
                tileid: props.tileId,
            });
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
            <ResourceInstanceMultiSelectWidget
                graph-slug="scheme"
                node-alias="creation_sources"
                :initial-value="props.tileData?.creation_sources"
                :mode="EDIT"
            />
        </Form>
    </div>
</template>
