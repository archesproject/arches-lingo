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

import NonLocalizedStringWidget from "@/arches_component_lab/widgets/NonLocalizedStringWidget/NonLocalizedStringWidget.vue";
import ReferenceSelectWidget from "@/arches_controlled_lists/widgets/ReferenceSelectWidget/ReferenceSelectWidget.vue";
import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

import { createScheme, upsertLingoTile } from "@/arches_lingo/api.ts";

import {
    DEFAULT_ERROR_TOAST_LIFE,
    EDIT,
    ERROR,
} from "@/arches_lingo/constants.ts";

import type { FormSubmitEvent } from "@primevue/forms";
import type { SchemeRights } from "@/arches_lingo/types";

const props = defineProps<{
    tileData: SchemeRights | undefined;
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

        // TODO: in future versions hit an API for expected shape &&
        // recursively map the form data to the expected shape
        const expectedTileShape = {
            right_holder: formData.right_holder,
            right_type: formData.right_type,
            right_statement: {
                right_statement_content: formData.right_statement_content,
                right_statement_language: formData.right_statement_language,
                right_statement_type: formData.right_statement_type,
                right_statement_type_metatype:
                    formData.right_statement_type_metatype,
            },
        };

        let updatedTileId;

        if (!props.resourceInstanceId) {
            const updatedScheme = await createScheme({
                [props.nodegroupAlias]: expectedTileShape,
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
                    ...expectedTileShape,
                    tileid: props.tileId,
                },
            );

            updatedTileId = updatedScheme.tileid;
        }

        openEditor!(props.componentName, updatedTileId);
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to save data."),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        refreshReportSection!(props.componentName);
        isSaving.value = false;
    }
}
</script>

<template>
    <ProgressSpinner
        v-if="isSaving"
        style="width: 100%"
    />

    <h3 v-show="!isSaving">{{ props.sectionTitle }}</h3>

    <Form
        v-show="!isSaving"
        ref="form"
        @submit="save"
    >
        <ResourceInstanceMultiSelectWidget
            node-alias="right_holder"
            :graph-slug="props.graphSlug"
            :initial-value="props.tileData?.right_holder"
            :mode="EDIT"
        />
        <ReferenceSelectWidget
            node-alias="right_type"
            :graph-slug="props.graphSlug"
            :initial-value="props.tileData?.right_type"
            :mode="EDIT"
        />
        <NonLocalizedStringWidget
            node-alias="right_statement_content"
            :graph-slug="props.graphSlug"
            :initial-value="
                props.tileData?.right_statement?.right_statement_content
            "
            :mode="EDIT"
        />
        <ReferenceSelectWidget
            node-alias="right_statement_language"
            :graph-slug="props.graphSlug"
            :initial-value="
                props.tileData?.right_statement?.right_statement_language
            "
            :mode="EDIT"
        />
        <ReferenceSelectWidget
            node-alias="right_statement_type"
            :graph-slug="props.graphSlug"
            :initial-value="
                props.tileData?.right_statement?.right_statement_type
            "
            :mode="EDIT"
        />
        <ReferenceSelectWidget
            node-alias="right_statement_type_metatype"
            :graph-slug="props.graphSlug"
            :initial-value="
                props.tileData?.right_statement?.right_statement_type_metatype
            "
            :mode="EDIT"
        />
    </Form>
</template>
