<script setup lang="ts">
import { inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

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
                <GenericWidget
                    node-alias="statement_content"
                    :graph-slug="props.graphSlug"
                    :value="rowData.aliased_data.statement_content"
                    :mode="VIEW"
                    :should-show-label="false"
                />
            </template>
            <template #type="{ rowData }">
                <GenericWidget
                    node-alias="statement_type"
                    :graph-slug="props.graphSlug"
                    :value="rowData.aliased_data.statement_type"
                    :mode="VIEW"
                    :should-show-label="false"
                />
            </template>
            <template #language="{ rowData }">
                <GenericWidget
                    node-alias="statement_language"
                    :graph-slug="props.graphSlug"
                    :value="rowData.aliased_data.statement_language"
                    :mode="VIEW"
                    :should-show-label="false"
                />
            </template>
            <template #drawer="{ rowData }">
                <GenericWidget
                    node-alias="statement_data_assignment_object_used"
                    :graph-slug="props.graphSlug"
                    :value="rowData.statement_data_assignment_object_used"
                    :mode="VIEW"
                />
                <GenericWidget
                    node-alias="statement_data_assignment_actor"
                    :graph-slug="props.graphSlug"
                    :value="rowData.statement_data_assignment_actor"
                    :mode="VIEW"
                />
            </template>
        </MetaStringViewer>
    </div>
</template>
