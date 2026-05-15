<script setup lang="ts">
import { inject, computed } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Tag from "primevue/tag";

import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

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
const { isEditor } = useUserStore();

const openEditor =
    inject<(componentName: string, tileId?: string) => void>("openEditor");

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
            "Create a Concept Label before adding matched concepts",
        );
    }

    return $gettext(
        "This concept is not editable in its current lifecycle state",
    );
});

const metaStringLabel = computed<MetaStringText>(() => ({
    deleteConfirm: $gettext(
        "Are you sure you want to delete this relationship?",
    ),
    name: $gettext("Match Type"),
    type: $gettext("Related URI"),
    noRecords: $gettext("No matched concepts were found."),
    sortFields: {
        name: "aliased_data.match_status_ascribed_relation",
        type: "aliased_data.match_status_ascribed_comparate",
    },
}));

function matchedConceptURIIsLink(rowData: ConceptMatchStatus): boolean {
    const uri = rowData.aliased_data
        .match_status_ascribed_comparate as unknown as
        | string
        | null
        | undefined;
    return Boolean(uri?.startsWith("http"));
}
</script>

<template>
    <div class="viewer-section">
        <div class="section-header">
            <div class="section-title">
                <h2>{{ props.sectionTitle }}</h2>
                <Tag
                    v-if="props.tileData.length"
                    :value="String(props.tileData.length)"
                    severity="secondary"
                />
            </div>

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
                    :value="
                        rowData.aliased_data.match_status_ascribed_relation ??
                        null
                    "
                    :mode="VIEW"
                    :should-show-label="false"
                />
            </template>
            <template #type="{ rowData }">
                <Button
                    v-if="matchedConceptURIIsLink(rowData)"
                    :label="
                        rowData.aliased_data
                            .match_status_ascribed_comparate as unknown as string
                    "
                    variant="link"
                    as="a"
                    :href="
                        rowData.aliased_data
                            .match_status_ascribed_comparate as unknown as string
                    "
                    target="_blank"
                    rel="noopener"
                ></Button>
                <span v-else>
                    {{ rowData.aliased_data.match_status_ascribed_comparate }}
                </span>
            </template>
            <template #drawer="{ rowData }">
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="match_status_data_assignment_actor"
                    :value="
                        rowData.aliased_data
                            .match_status_data_assignment_actor ?? null
                    "
                    :mode="VIEW"
                />
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="match_status_data_assignment_object_used"
                    :value="
                        rowData.aliased_data
                            .match_status_data_assignment_object_used ?? null
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
