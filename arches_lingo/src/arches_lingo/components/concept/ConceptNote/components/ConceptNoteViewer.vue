<script setup lang="ts">
import { inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import NonLocalizedStringWidget from "@/arches_component_lab/widgets/NonLocalizedStringWidget/NonLocalizedStringWidget.vue";
import ReferenceSelectWidget from "@/arches_controlled_lists/widgets/ReferenceSelectWidget/ReferenceSelectWidget.vue";
import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";

import type { MetaStringText, ConceptStatement } from "@/arches_lingo/types.ts";

const props = defineProps<{
    tileData: ConceptStatement[] | undefined;
    componentName: string;
    sectionTitle: string;
    graphSlug: string;
    nodegroupAlias: string;
}>();

const { $gettext } = useGettext();

const openEditor = inject<(componentName: string) => void>("openEditor");

const metaStringLabel: MetaStringText = {
    deleteConfirm: $gettext("Are you sure you want to delete this note?"),
    language: $gettext("Language"),
    name: $gettext("Note"),
    type: $gettext("Type"),
    noRecords: $gettext("No concept notes were found."),
};
</script>

<template>
    <div class="section">
        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>

            <Button
                :label="$gettext('Add Note')"
                class="add-button"
                @click="openEditor!(props.componentName)"
            ></Button>
        </div>

        <MetaStringViewer
            :meta-strings="props.tileData"
            :meta-string-text="metaStringLabel"
            :component-name="props.componentName"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
        >
            <template #name="{ rowData }">
                <NonLocalizedStringWidget
                    node-alias="statement_content"
                    :graph-slug="props.graphSlug"
                    :initial-value="rowData.aliased_data.statement_content"
                    :mode="VIEW"
                    :show-label="false"
                />
            </template>
            <template #type="{ rowData }">
                <ReferenceSelectWidget
                    node-alias="statement_type"
                    :graph-slug="props.graphSlug"
                    :initial-value="rowData.aliased_data.statement_type"
                    :mode="VIEW"
                    :show-label="false"
                />
            </template>
            <template #language="{ rowData }">
                <ReferenceSelectWidget
                    node-alias="statement_language"
                    :graph-slug="props.graphSlug"
                    :initial-value="rowData.aliased_data.statement_language"
                    :mode="VIEW"
                    :show-label="false"
                />
            </template>
            <template #drawer="{ rowData }">
                <ResourceInstanceMultiSelectWidget
                    node-alias="statement_data_assignment_object_used"
                    :graph-slug="props.graphSlug"
                    :initial-value="rowData.statement_data_assignment_object_used"
                    :mode="VIEW"
                />
                <ResourceInstanceMultiSelectWidget
                    node-alias="statement_data_assignment_actor"
                    :graph-slug="props.graphSlug"
                    :initial-value="rowData.statement_data_assignment_actor"
                    :mode="VIEW"
                />
            </template>
        </MetaStringViewer>
    </div>
</template>

<style scoped>
.section {
    padding: 1rem 1rem 1.25rem 1rem;
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--p-form-field-border-color);
    padding-bottom: .5rem;
}

h2 {
    margin: 0;
    font-size: 1.2rem;
    font-weight: 400;
    color: var(--p-neutral-500);
}

.add-button {
    height: 2.0rem;
    font-size: 0.9rem;
    font-weight: 400;
    min-width: 10rem;
    border-radius: 2px;
}

:deep(.p-datatable-header-cell) {
    padding: 0.9rem 1rem;
}

:deep(.p-datatable-tbody > tr > td ) {
    font-size: .95rem;
    padding: .4rem 1rem;
}

:deep(.p-datatable-column-title) {
    font-weight: 400;
    color: var(--p-neutral-500);
}

:deep(.p-datatable-row-expansion td) {
    padding: 1rem 0rem;
}

:deep(.controls) {
    flex-direction: row-reverse;
}

:deep(.controls button) {
    border-radius: 50%;
    margin: 0 0.15rem;
}
</style>
