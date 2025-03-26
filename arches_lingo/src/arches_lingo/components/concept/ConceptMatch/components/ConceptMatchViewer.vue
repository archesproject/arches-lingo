<script setup lang="ts">
import { inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import UrlWidget from "@/arches_lingo/components/widgets/UrlWidget/UrlWidget.vue";

import ConceptResourceSelectWidget from "@/arches_lingo/components/widgets/ConceptResourceSelectWidget/ConceptResourceSelectWidget.vue";
import ReferenceSelectWidget from "@/arches_controlled_lists/widgets/ReferenceSelectWidget/ReferenceSelectWidget.vue";
import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";

import type {
    ConceptMatchStatus,
    MetaStringText,
} from "@/arches_lingo/types.ts";

const props = defineProps<{
    tileData: ConceptMatchStatus[];
    componentName: string;
    sectionTitle: string;
    graphSlug: string;
    nodegroupAlias: string;
}>();

const { $gettext } = useGettext();

const openEditor = inject<(componentName: string) => void>("openEditor");

const metaStringLabel: MetaStringText = {
    deleteConfirm: $gettext(
        "Are you sure you want to delete this relationship?",
    ),
    name: $gettext("Match Type"),
    type: $gettext("Related URI"),
    language: $gettext("Related Label"),
    noRecords: $gettext("No matched concepts were found."),
};
</script>

<template>
    <div class="section-header">
        <h2>{{ props.sectionTitle }}</h2>

        <Button
            :label="$gettext('Add New Concept Label')"
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
            <ReferenceSelectWidget
                :graph-slug="props.graphSlug"
                node-alias="match_status_ascribed_relation"
                :initial-value="rowData.match_status_ascribed_relation"
                :mode="VIEW"
                :show-label="false"
            />
        </template>
        <template #type="{ rowData }">
            <UrlWidget
                :graph-slug="props.graphSlug"
                node-alias="uri_content"
                :initial-value="rowData.uri"
                :mode="VIEW"
                :show-label="false"
            />
        </template>
        <template #language="{ rowData }">
            <ConceptResourceSelectWidget
                :graph-slug="props.graphSlug"
                node-alias="match_status_ascribed_comparate"
                :initial-value="rowData.match_status_ascribed_comparate"
                :mode="VIEW"
                :show-label="false"
            />
        </template>
        <template #drawer="{ rowData }">
            <ResourceInstanceMultiSelectWidget
                :graph-slug="props.graphSlug"
                node-alias="match_status_data_assignment_actor"
                :initial-value="rowData.match_status_data_assignment_actor"
                :mode="VIEW"
            />
            <ResourceInstanceMultiSelectWidget
                :graph-slug="props.graphSlug"
                node-alias="match_status_data_assignment_object_used"
                :initial-value="
                    rowData.match_status_data_assignment_object_used
                "
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
