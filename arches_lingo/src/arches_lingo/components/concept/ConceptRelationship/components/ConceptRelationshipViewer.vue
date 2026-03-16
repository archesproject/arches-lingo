<script setup lang="ts">
import { inject, computed } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";
import ConceptResourceSelectWidget from "@/arches_lingo/components/widgets/ConceptResourceSelectWidget/ConceptResourceSelectWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

import type {
    ConceptRelationStatus,
    MetaStringText,
} from "@/arches_lingo/types.ts";

const props = defineProps<{
    componentName: string;
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId: string | undefined;
    sectionTitle: string;
    tileData: ConceptRelationStatus[];
}>();

const { $gettext } = useGettext();
const { isEditor } = useUserStore();

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
        return $gettext(
            "Create a Concept Label before adding associated concepts",
        );
    }

    return $gettext(
        "This concept is not editable in its current lifecycle state",
    );
});

const metaStringLabel: MetaStringText = {
    deleteConfirm: $gettext(
        "Are you sure you want to delete this relationship?",
    ),
    name: $gettext("Relationship"),
    type: $gettext("Related Concept"),
    noRecords: $gettext("No associated concepts were found."),
    sortFields: {
        name: "aliased_data.relation_status_ascribed_comparate.display_value",
        type: "aliased_data.relation_status_ascribed_relation.display_value",
        language:
            "aliased_data.relation_status_ascribed_comparate.display_value",
    },
};
</script>

<template>
    <div class="viewer-section">
        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>

            <Button
                v-if="isEditor"
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
                :label="$gettext('Add Associated Concept')"
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
                    node-alias="relation_status_ascribed_relation"
                    :aliased-node-data="
                        rowData.aliased_data.relation_status_ascribed_relation
                    "
                    :mode="VIEW"
                    :should-show-label="false"
                />
            </template>
            <template #type="{ rowData }">
                <ConceptResourceSelectWidget
                    :graph-slug="props.graphSlug"
                    node-alias="relation_status_ascribed_comparate"
                    :aliased-node-data="
                        rowData.aliased_data.relation_status_ascribed_comparate
                    "
                    :mode="VIEW"
                    :should-show-label="false"
                />
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
