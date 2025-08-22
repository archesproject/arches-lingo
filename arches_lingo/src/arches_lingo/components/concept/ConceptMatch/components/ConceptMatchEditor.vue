<script setup lang="ts">
import { inject, ref, useTemplateRef, watch } from "vue";

import { useRouter } from "vue-router";
import { Form } from "@primevue/forms";

import Skeleton from "primevue/skeleton";

import DateWidget from "@/arches_component_lab/widgets/DateWidget/DateWidget.vue";
import ReferenceSelectWidget from "@/arches_controlled_lists/widgets/ReferenceSelectWidget/ReferenceSelectWidget.vue";
import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

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

            updatedTileId = updatedConcept[props.nodegroupAlias][0].tileid;
        } else {
            const updatedConcept = await upsertLingoTile(
                props.graphSlug,
                props.nodegroupAlias,
                {
                    resourceinstance: props.resourceInstanceId,
                    aliased_data: { ...formData },
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
        <div class="form-header">
            <h3>{{ props.sectionTitle }}</h3>
            <div class="form-description">
                {{ $gettext("Match concepts from other schemes that may be associated with this concept.") }}
            </div>
        </div>

        <div class="form-container">
            <Form
                ref="form"
                @submit="save"
            >
                <div class="widget-container column">
                    <ResourceInstanceMultiSelectWidget
                        :graph-slug="props.graphSlug"
                        node-alias="match_status_ascribed_comparate"
                        :value="
                            props.tileData?.aliased_data.match_status_ascribed_comparate
                                ?.interchange_value
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <ReferenceSelectWidget
                        :graph-slug="props.graphSlug"
                        node-alias="match_status_ascribed_relation"
                        :value="
                            props.tileData?.aliased_data.match_status_ascribed_relation
                                ?.interchange_value
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <ReferenceSelectWidget
                        :graph-slug="props.graphSlug"
                        node-alias="match_status_status"
                        :value="
                            props.tileData?.aliased_data.match_status_status
                                ?.interchange_value
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <ReferenceSelectWidget
                        :graph-slug="props.graphSlug"
                        node-alias="match_status_status_metatype"
                        :value="
                            props.tileData?.aliased_data.match_status_status_metatype
                                ?.interchange_value
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container">
                    <DateWidget
                        :graph-slug="props.graphSlug"
                        node-alias="match_status_timespan_begin_of_the_begin"
                        :value="
                            props.tileData?.aliased_data
                                .match_status_timespan_begin_of_the_begin
                                ?.interchange_value
                        "
                        :mode="EDIT"
                    />
                    <DateWidget
                        :graph-slug="props.graphSlug"
                        node-alias="match_status_timespan_end_of_the_end"
                        :value="
                            props.tileData?.aliased_data
                                .match_status_timespan_end_of_the_end?.interchange_value
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <ResourceInstanceMultiSelectWidget
                        :graph-slug="props.graphSlug"
                        node-alias="match_status_data_assignment_actor"
                        :value="
                            props.tileData?.aliased_data
                                .match_status_data_assignment_actor?.interchange_value
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <ResourceInstanceMultiSelectWidget
                        :graph-slug="props.graphSlug"
                        node-alias="match_status_data_assignment_object_used"
                        :value="
                            props.tileData?.aliased_data
                                .match_status_data_assignment_object_used
                                ?.interchange_value
                        "
                        :mode="EDIT"
                    />
                </div>
                <div class="widget-container column">
                    <ReferenceSelectWidget
                        :graph-slug="props.graphSlug"
                        node-alias="match_status_data_assignment_type"
                        :value="
                            props.tileData?.aliased_data
                                .match_status_data_assignment_type?.interchange_value
                        "
                        :mode="EDIT"
                    />
                </div>
            </Form>
        </div>
    </div>
</template>
<style scoped>
.form-header {
    padding-top: 0rem;
    padding-bottom: 1rem;
    background: var(--p-header-background);
    border-bottom: 0.06rem solid var(--p-header-border);
    min-height: 5.5rem;
}

.form-header h3 {
    margin: 0;
    padding: 0.5rem 1rem 0 1rem;
}

.form-container {
    padding: 0.5rem 1rem;
    background: var(--p-editor-form-background);
}

.form-description {
    padding: 0.125rem 1rem;
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
    margin-inline-end: 0.25rem;
}

.widget-container {
    display: flex; 
    gap: .25rem; 
    padding: .5rem 0rem 0.25rem 0rem;
    color: var(--p-header-item-label);
}

.column {
    flex-direction: column;
}

:deep(.p-inputtext) {
    border-radius: .125rem;
}

:deep(.p-treeselect) {
    border-radius: .125rem;
}

:deep(.p-multiselect) {
    border-radius: .125rem;
}
</style>