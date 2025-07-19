<script setup lang="ts">
import { inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import URLWidget from "@/arches_component_lab/widgets/URLWidget/URLWidget.vue";

import ReferenceSelectWidget from "@/arches_controlled_lists/widgets/ReferenceSelectWidget/ReferenceSelectWidget.vue";
import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";

import { routeNames } from "@/arches_lingo/routes.ts";

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

const openEditor =
    inject<(componentName: string, tileId?: string) => void>("openEditor");

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
    <div class="viewer-section">
        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>

            <Button
                class="add-button"
                style="min-width: 15rem"
                @click="openEditor!(props.componentName)"
            >
                <span><i class="pi pi-plus-circle"></i></span>
                <span>{{$gettext('Add Matched Concept')}}</span>
            </Button>
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
                    :value="
                        rowData.aliased_data.match_status_ascribed_relation
                            ?.interchange_value
                    "
                    :mode="VIEW"
                    :show-label="false"
                />
            </template>
            <template #type="{ rowData }">
                <URLWidget
                    :graph-slug="props.graphSlug"
                    node-alias="uri_content"
                    :value="rowData.aliased_data.uri?.interchange_value"
                    :mode="VIEW"
                    :show-label="false"
                />
            </template>
            <template #language="{ rowData }">
                <div
                    v-for="item in rowData.aliased_data
                        .match_status_ascribed_comparate?.interchange_value"
                    :key="item.resource_id"
                >
                    <RouterLink
                        :to="{
                            name: routeNames.concept,
                            params: {
                                id: item.resource_id,
                            },
                        }"
                        class="text-link"
                    >
                        {{ item.display_value }}
                    </RouterLink>
                </div>
            </template>
            <template #drawer="{ rowData }">
                <ResourceInstanceMultiSelectWidget
                    :graph-slug="props.graphSlug"
                    node-alias="match_status_data_assignment_actor"
                    :value="
                        rowData.aliased_data.match_status_data_assignment_actor
                            ?.interchange_value
                    "
                    :mode="VIEW"
                />
                <ResourceInstanceMultiSelectWidget
                    :graph-slug="props.graphSlug"
                    node-alias="match_status_data_assignment_object_used"
                    :value="
                        rowData.match_status_data_assignment_object_used
                            ?.interchange_value
                    "
                    :mode="VIEW"
                />
            </template>
        </MetaStringViewer>
    </div>
</template>

<style scoped>
.text-link {
    color: var(--p-primary-500);
}

:deep(a) {
    color: var(--p-primary-500);
}
</style>
