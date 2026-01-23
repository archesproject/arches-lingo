<script setup lang="ts">
import { inject, computed } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";

import type { MetaStringText, ConceptStatement } from "@/arches_lingo/types.ts";

const props = defineProps<{
    componentName: string;
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId: string | undefined;
    sectionTitle: string;
    tileData: ConceptStatement[] | undefined;
}>();

const { $gettext } = useGettext();

const openEditor = inject<(componentName: string) => void>("openEditor");

const resourceInstanceLifecycleState = inject<{
    value:
        | {
              can_edit_resource_instances: boolean;
              can_delete_resource_instances: boolean;
          }
        | undefined;
}>("resourceInstanceLifecycleState");

const canEditResourceInstances = computed(() => {
    return Boolean(
        resourceInstanceLifecycleState?.value?.can_edit_resource_instances,
    );
});

const isCreateDisabled = computed(() => {
    return Boolean(
        !props.resourceInstanceId || !canEditResourceInstances.value,
    );
});

const createTooltipText = computed(() => {
    if (!isCreateDisabled.value) {
        return "";
    }

    if (!props.resourceInstanceId) {
        return $gettext("Create a Concept Label before adding notes");
    }

    return $gettext(
        "This concept is not editable in its current lifecycle state",
    );
});

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
                v-tooltip.top="{
                    disabled: Boolean(!isCreateDisabled),
                    value: createTooltipText,
                    showDelay: 300,
                    pt: {
                        text: {
                            style: { fontFamily: 'var(--p-lingo-font-family)' },
                        },
                        arrow: { style: { display: 'none' } },
                    },
                }"
                :disabled="isCreateDisabled"
                :label="$gettext('Add Note')"
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
                    node-alias="statement_content"
                    :graph-slug="props.graphSlug"
                    :aliased-node-data="rowData.aliased_data.statement_content"
                    :mode="VIEW"
                    :should-show-label="false"
                />
            </template>
            <template #type="{ rowData }">
                <GenericWidget
                    node-alias="statement_type"
                    :graph-slug="props.graphSlug"
                    :aliased-node-data="rowData.aliased_data.statement_type"
                    :mode="VIEW"
                    :should-show-label="false"
                />
            </template>
            <template #language="{ rowData }">
                <GenericWidget
                    node-alias="statement_language"
                    :graph-slug="props.graphSlug"
                    :aliased-node-data="rowData.aliased_data.statement_language"
                    :mode="VIEW"
                    :should-show-label="false"
                />
            </template>
            <template #drawer="{ rowData }">
                <GenericWidget
                    node-alias="statement_data_assignment_object_used"
                    :graph-slug="props.graphSlug"
                    :aliased-node-data="
                        rowData.statement_data_assignment_object_used
                    "
                    :mode="VIEW"
                />
                <GenericWidget
                    node-alias="statement_data_assignment_actor"
                    :graph-slug="props.graphSlug"
                    :aliased-node-data="rowData.statement_data_assignment_actor"
                    :mode="VIEW"
                />
            </template>
        </MetaStringViewer>
    </div>
</template>
