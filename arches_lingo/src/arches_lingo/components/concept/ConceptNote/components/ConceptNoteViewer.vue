<script setup lang="ts">
import { inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import NonLocalizedTextAreaWidget from "@/arches_component_lab/widgets/NonLocalizedTextAreaWidget/NonLocalizedTextAreaWidget.vue";
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
    <div class="viewer-section">
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
                <NonLocalizedTextAreaWidget
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
                    :initial-value="
                        rowData.statement_data_assignment_object_used
                    "
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
