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

import Skeleton from "primevue/skeleton";

import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import { createLingoResource, upsertLingoTile } from "@/arches_lingo/api.ts";

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
        const formData = e.values;

        // TODO: in future versions hit an API for expected shape &&
        // recursively map the form data to the expected shape
        const expectedTileShape = {
            right_holder: formData.right_holder,
            right_type: formData.right_type,
            right_statement: {
                aliased_data: {
                    right_statement_content: formData.right_statement_content,
                    right_statement_language: formData.right_statement_language,
                    right_statement_type: formData.right_statement_type,
                    right_statement_type_metatype:
                        formData.right_statement_type_metatype,
                },
            },
        };

        let updatedTileId;

        if (!props.resourceInstanceId) {
            const updatedScheme = await createLingoResource(
                {
                    aliased_data: {
                        [props.nodegroupAlias]: {
                            aliased_data: expectedTileShape,
                        },
                    },
                },
                props.graphSlug,
            );

            await router.push({
                name: props.graphSlug,
                params: { id: updatedScheme.resourceinstanceid },
            });

            updatedTileId =
                updatedScheme.aliased_data[props.nodegroupAlias].tileid;
        } else {
            if (props.tileData?.aliased_data.right_statement?.tileid) {
                (
                    expectedTileShape.right_statement as Record<string, unknown>
                ).tileid = props.tileData.aliased_data.right_statement.tileid;
            }

            const updatedTile = await upsertLingoTile(
                props.graphSlug,
                props.nodegroupAlias,
                {
                    resourceinstance: props.resourceInstanceId,
                    aliased_data: { ...expectedTileShape },
                    tileid: props.tileId,
                },
            );

            updatedTileId = updatedTile.tileid;
        }

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
                node-alias="right_statement_content"
                :graph-slug="props.graphSlug"
                :aliased-node-data="
                    props.tileData?.aliased_data.right_statement?.aliased_data
                        .right_statement_content
                "
                :mode="EDIT"
            />
            <GenericWidget
                node-alias="right_statement_type"
                :graph-slug="props.graphSlug"
                :aliased-node-data="
                    props.tileData?.aliased_data.right_statement?.aliased_data
                        .right_statement_type
                "
                :mode="EDIT"
            />
            <GenericWidget
                node-alias="right_statement_language"
                :graph-slug="props.graphSlug"
                :aliased-node-data="
                    props.tileData?.aliased_data.right_statement?.aliased_data
                        .right_statement_language
                "
                :mode="EDIT"
            />
            <GenericWidget
                node-alias="right_holder"
                :graph-slug="props.graphSlug"
                :aliased-node-data="props.tileData?.aliased_data.right_holder"
                :mode="EDIT"
            />
            <GenericWidget
                node-alias="right_type"
                :graph-slug="props.graphSlug"
                :aliased-node-data="props.tileData?.aliased_data.right_type"
                :mode="EDIT"
            />
        </Form>
    </div>
</template>
