<script setup lang="ts">
import { inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";

import NonLocalizedStringWidget from "@/arches_component_lab/widgets/NonLocalizedStringWidget/NonLocalizedStringWidget.vue";
import ReferenceSelectWidget from "@/arches_controlled_lists/widgets/ReferenceSelectWidget/ReferenceSelectWidget.vue";
import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";

import type {
    AppellativeStatus,
    MetaStringText,
} from "@/arches_lingo/types.ts";

const props = defineProps<{
    tileData: AppellativeStatus[];
    componentName: string;
    sectionTitle: string;
    graphSlug: string;
    nodegroupAlias: string;
}>();

const { $gettext } = useGettext();

const openEditor = inject<(componentName: string) => void>("openEditor");

const metaStringLabel: MetaStringText = {
    deleteConfirm: $gettext("Are you sure you want to delete this label?"),
    language: $gettext("Language"),
    name: $gettext("Label"),
    type: $gettext("Type"),
    noRecords: $gettext("No concept labels were found."),
};
</script>

<template>
    <div class="section">
        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>

            <Button
                :label="$gettext('Add Label')"
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
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_ascribed_name_content"
                    :initial-value="
                        rowData.aliased_data
                            .appellative_status_ascribed_name_content
                    "
                    :mode="VIEW"
                    :show-label="false"
                />
            </template>
            <template #type="{ rowData }">
                <ReferenceSelectWidget
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_ascribed_relation"
                    :initial-value="
                        rowData.aliased_data.appellative_status_ascribed_relation
                    "
                    :mode="VIEW"
                    :show-label="false"
                />
            </template>
            <template #language="{ rowData }">
                <ReferenceSelectWidget
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_ascribed_name_language"
                    :initial-value="
                        rowData.aliased_data
                            .appellative_status_ascribed_name_language
                    "
                    :mode="VIEW"
                    :show-label="false"
                />
            </template>
            <template #drawer="{ rowData }">
                <ResourceInstanceMultiSelectWidget
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_data_assignment_object_used"
                    :initial-value="
                        rowData.aliased_data
                            .appellative_status_data_assignment_object_used
                    "
                    :mode="VIEW"
                />
                <ResourceInstanceMultiSelectWidget
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_data_assignment_actor"
                    :initial-value="
                        rowData.aliased_data
                            .appellative_status_data_assignment_actor
                    "
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
    align-items: baseline;
    border-bottom: 1px solid var(--p-form-field-border-color);
    padding-bottom: .5rem;
}

h2 {
    margin: 0;
    font-size: 1.1rem;
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
    padding: 0.5rem 0rem;
}

:deep(.controls) {
    flex-direction: row-reverse;
}

:deep(.controls button) {
    border-radius: 50%;
    margin: 0 0.15rem;
}
</style>
