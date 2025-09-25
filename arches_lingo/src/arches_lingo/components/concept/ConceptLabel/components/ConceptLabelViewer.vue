<script setup lang="ts">
import { inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";

import type {
    AppellativeStatus,
    MetaStringText,
} from "@/arches_lingo/types.ts";

const props = defineProps<{
    componentName: string;
    graphSlug: string;
    resourceInstanceId: string | undefined;
    sectionTitle: string;
    nodegroupAlias: string;
    tileData: AppellativeStatus[];
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
    <div class="viewer-section">
        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>

            <Button
                :label="$gettext('Add Label')"
                class="add-button"
                icon="pi pi-plus-circle"
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
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_ascribed_name_content"
                    :aliased-node-data="
                        rowData.aliased_data
                            .appellative_status_ascribed_name_content
                    "
                    :mode="VIEW"
                    :should-show-label="false"
                />
            </template>
            <template #type="{ rowData }">
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_ascribed_relation"
                    :aliased-node-data="
                        rowData.aliased_data
                            .appellative_status_ascribed_relation
                    "
                    :mode="VIEW"
                    :should-show-label="false"
                />
            </template>
            <template #language="{ rowData }">
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_ascribed_name_language"
                    :aliased-node-data="
                        rowData.aliased_data
                            .appellative_status_ascribed_name_language
                    "
                    :mode="VIEW"
                    :should-show-label="false"
                />
            </template>
            <template #drawer="{ rowData }">
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_data_assignment_object_used"
                    :aliased-node-data="
                        rowData.aliased_data
                            .appellative_status_data_assignment_object_used
                    "
                    :mode="VIEW"
                />
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="appellative_status_data_assignment_actor"
                    :aliased-node-data="
                        rowData.aliased_data
                            .appellative_status_data_assignment_actor
                    "
                    :mode="VIEW"
                />
            </template>
        </MetaStringViewer>
    </div>
</template>
