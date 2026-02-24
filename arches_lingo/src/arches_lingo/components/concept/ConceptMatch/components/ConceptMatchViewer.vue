<script setup lang="ts">
import { inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";

import type {
    ConceptMatchStatus,
    MetaStringText,
} from "@/arches_lingo/types.ts";

const props = defineProps<{
    componentName: string;
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId: string | undefined;
    sectionTitle: string;
    tileData: ConceptMatchStatus[];
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
    noRecords: $gettext("No matched concepts were found."),
};

function matchedConceptURIIsLink(rowData: ConceptMatchStatus): boolean {
    const uri = rowData.aliased_data.match_status_ascribed_comparate
        .display_value as string;
    return uri.startsWith("http");
}
</script>

<template>
    <div class="viewer-section">
        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>

            <Button
                v-tooltip.top="{
                    disabled: Boolean(props.resourceInstanceId),
                    value: $gettext(
                        'Create a Concept Label before adding matched concepts',
                    ),
                    showDelay: 300,
                    pt: {
                        text: {
                            style: { fontFamily: 'var(--p-lingo-font-family)' },
                        },
                        arrow: { style: { display: 'none' } },
                    },
                }"
                :disabled="Boolean(!props.resourceInstanceId)"
                :label="$gettext('Add Matched Concept')"
                class="add-button wide"
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
                    node-alias="match_status_ascribed_relation"
                    :aliased-node-data="
                        rowData.aliased_data.match_status_ascribed_relation
                    "
                    :mode="VIEW"
                    :should-show-label="false"
                />
            </template>
            <template #type="{ rowData }">
                <Button
                    v-if="matchedConceptURIIsLink(rowData)"
                    :label="
                        rowData.aliased_data.match_status_ascribed_comparate
                            .display_value
                    "
                    variant="link"
                    as="a"
                    :href="
                        rowData.aliased_data.match_status_ascribed_comparate
                            .display_value
                    "
                    target="_blank"
                    rel="noopener"
                ></Button>
                <span v-else>
                    {{
                        rowData.aliased_data.match_status_ascribed_comparate
                            .display_value
                    }}
                </span>
            </template>
            <template #drawer="{ rowData }">
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="match_status_data_assignment_actor"
                    :aliased-node-data="
                        rowData.aliased_data.match_status_data_assignment_actor
                    "
                    :mode="VIEW"
                />
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="match_status_data_assignment_object_used"
                    :aliased-node-data="
                        rowData.aliased_data
                            .match_status_data_assignment_object_used
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
    padding-left: 0;

    span {
        font-size: var(--p-lingo-font-size-smallnormal);
    }
}
</style>
