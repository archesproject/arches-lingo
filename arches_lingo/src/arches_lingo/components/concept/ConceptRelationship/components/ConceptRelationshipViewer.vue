<script setup lang="ts">
import { inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import type {
    ConceptRelationStatus,
    MetaStringText,
} from "@/arches_lingo/types.ts";

const props = defineProps<{
    tileData: ConceptRelationStatus[];
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
    name: $gettext("RelationshipID"),
    type: $gettext("Relationship"),
    language: $gettext("Related Concept"),
    noRecords: $gettext("No associated concepts were found."),
};
</script>

<template>
    <div class="viewer-section">
        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>

            <Button
                :label="$gettext('Add Associated Concept')"
                class="add-button"
                style="min-width: 15rem"
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
                <div
                    v-for="item in rowData.aliased_data
                        .relation_status_ascribed_comparate?.node_value"
                    :key="item.resource_id"
                    style="white-space: nowrap"
                >
                    <!-- non-standard -- we only want to display the resource ID -->
                    <GenericWidget
                        :graph-slug="props.graphSlug"
                        node-alias="relation_status_ascribed_comparate"
                        :aliased-node-data="item.resource_id"
                        :mode="VIEW"
                        :should-show-label="false"
                    />
                </div>
            </template>
            <template #type="{ rowData }">
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="relation_status_ascribed_relation"
                    :aliased-node-data="
                        rowData.aliased_data.relation_status_ascribed_relation
                    "
                    :mode="VIEW"
                    :should-show-label="false"
                />
            </template>
            <template #language="{ rowData }">
                <div
                    v-for="item in rowData.aliased_data
                        .relation_status_ascribed_comparate.node_value"
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
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="relation_status_data_assignment_actor"
                    :aliased-node-data="
                        rowData.aliased_data
                            .relation_status_data_assignment_actor
                    "
                    :mode="VIEW"
                />
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="relation_status_data_assignment_object_used"
                    :aliased-node-data="
                        rowData.relation_status_data_assignment_object_used
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
</style>
