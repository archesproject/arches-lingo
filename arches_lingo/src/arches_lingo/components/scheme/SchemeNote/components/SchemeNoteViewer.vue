<script setup lang="ts">
import { inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import NonLocalizedStringWidget from "@/arches_component_lab/widgets/NonLocalizedStringWidget/NonLocalizedStringWidget.vue";
import ReferenceSelectWidget from "@/arches_controlled_lists/widgets/ReferenceSelectWidget/ReferenceSelectWidget.vue";
import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";

import type { MetaStringText, SchemeStatement } from "@/arches_lingo/types.ts";

const props = defineProps<{
    tileData: SchemeStatement[] | undefined;
    componentName: string;
    sectionTitle: string;
    graphSlug: string;
    nodegroupAlias: string;
}>();

const { $gettext } = useGettext();

const openEditor = inject<(componentName: string) => void>("openEditor");

const metaStringLabel: MetaStringText = {
    deleteConfirm: $gettext("Are you sure you want to delete this note?"),
    language: $gettext("Note Language"),
    name: $gettext("Note Name"),
    type: $gettext("Note Type"),
    noRecords: $gettext("No scheme notes were found."),
};
</script>

<template>
    <div class="section-header">
        <h2>{{ props.sectionTitle }}</h2>

        <Button
            :label="$gettext('Add New Scheme Note')"
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
                node-alias="statement_content_n1"
                :graph-slug="props.graphSlug"
                :initial-value="rowData.statement_content_n1"
                :mode="VIEW"
                :show-label="false"
            />
        </template>
        <template #type="{ rowData }">
            <ReferenceSelectWidget
                node-alias="statement_type_n1"
                :graph-slug="props.graphSlug"
                :initial-value="rowData.statement_type_n1"
                :mode="VIEW"
                :show-label="false"
            />
        </template>
        <template #language="{ rowData }">
            <ReferenceSelectWidget
                node-alias="statement_language_n1"
                :graph-slug="props.graphSlug"
                :initial-value="rowData.statement_language_n1"
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
</template>

<style scoped>
.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 0.125rem solid var(--p-menubar-border-color);
}
</style>
