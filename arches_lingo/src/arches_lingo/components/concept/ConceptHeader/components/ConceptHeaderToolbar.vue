<script setup lang="ts">
import { computed, inject, ref } from "vue";

import { useGettext } from "vue3-gettext";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import { storeToRefs } from "pinia";

import Button from "primevue/button";

import DeleteConceptDialog from "@/arches_lingo/components/concept/ConceptHeader/components/DeleteConceptDialog.vue";
import ExportThesauri from "@/arches_lingo/components/scheme/SchemeHeader/components/ExportThesauri.vue";
import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import {
    deleteConcept,
    retireConcept,
    upsertLingoTile,
} from "@/arches_lingo/api.ts";
import {
    CONCEPT_ICON,
    CONCEPT_TYPE_NODE_ALIAS,
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    DELETE,
    DEPRECATE,
    EDIT,
    ERROR,
    GUIDE_TERM_ICON,
    GUIDE_TERM_URI,
    NEW_CONCEPT,
    RETIRED_LIFECYCLE_STATE_ID,
    SUCCESS,
    TOP_CONCEPT_ICON,
    VIEW,
} from "@/arches_lingo/constants.ts";

import { routeNames } from "@/arches_lingo/routes.ts";
import { navigateToSchemeOrConcept } from "@/arches_lingo/utils.ts";

import { useEditLog } from "@/arches_lingo/composables/useEditLog.ts";
import { useResourceStore } from "@/arches_lingo/composables/useResourceStore.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

import type { Ref } from "vue";
import type {
    DeleteConceptStrategy,
    ResourceInstanceLifecycleState,
    ResourceInstanceResult,
} from "@/arches_lingo/types.ts";
import type { Label } from "@/arches_controlled_lists/types.ts";
import type { ReferenceSelectValue } from "@/arches_controlled_lists/datatypes/reference-select/types.ts";

const props = defineProps<{
    concept: ResourceInstanceResult | undefined;
    label: Label | undefined;
    graphSlug: string;
    resourceInstanceId: string | undefined;
    conceptTypeTile:
        | {
              tileid?: string;
              aliased_data?: Record<string, { node_value?: unknown }>;
          }
        | undefined;
    isTopConcept: boolean;
}>();

const resourceInstanceLifecycleState = inject<
    Ref<ResourceInstanceLifecycleState | undefined>
>("resourceInstanceLifecycleState");
const refreshSchemeHierarchy = inject<() => void>("refreshSchemeHierarchy");
const refreshReportSection = inject<(componentName: string) => void>(
    "refreshReportSection",
);

const { $gettext } = useGettext();
const toast = useToast();
const router = useRouter();

const { isEditor } = storeToRefs(useUserStore());
const resourceStore = useResourceStore();

const { openEditLog } = useEditLog(() => props.graphSlug);

const showExportDialog = ref(false);
const exportDialogKey = ref(0);
const showDeleteDialog = ref(false);
const dialogMode = ref<typeof DELETE | typeof DEPRECATE>(DELETE);

const lifecycleState = computed(function () {
    return resourceInstanceLifecycleState?.value;
});

const conceptIcon = computed(function () {
    const typeNodeValue =
        props.conceptTypeTile?.aliased_data?.[CONCEPT_TYPE_NODE_ALIAS]
            ?.node_value;
    if (isGuideTermType(typeNodeValue)) return GUIDE_TERM_ICON;
    if (props.isTopConcept) return TOP_CONCEPT_ICON;
    return CONCEPT_ICON;
});

const canEditResourceInstances = computed(function () {
    return (
        isEditor.value === true &&
        props.resourceInstanceId !== undefined &&
        lifecycleState.value?.can_edit_resource_instances === true
    );
});

const canDelete = computed(function () {
    return (
        isEditor.value === true &&
        props.resourceInstanceId !== undefined &&
        lifecycleState.value?.can_delete_resource_instances === true
    );
});

const canDeprecate = computed(function () {
    if (!isEditor.value || !props.resourceInstanceId) return false;
    const currentLifecycleState = lifecycleState.value;
    const canTransitionToRetired =
        currentLifecycleState?.next_resource_instance_lifecycle_states?.some(
            function (nextState) {
                return nextState.id === RETIRED_LIFECYCLE_STATE_ID;
            },
        );
    return (
        currentLifecycleState?.can_edit_resource_instances === true &&
        !currentLifecycleState?.can_delete_resource_instances &&
        canTransitionToRetired === true
    );
});

function isGuideTermType(typeNodeValue: unknown): boolean {
    if (!Array.isArray(typeNodeValue) || typeNodeValue.length === 0) {
        return false;
    }
    return typeNodeValue.some(
        (typeRef: { uri?: string }) => typeRef.uri === GUIDE_TERM_URI,
    );
}

async function onConceptTypeChange(newValue: ReferenceSelectValue) {
    try {
        await upsertLingoTile(props.graphSlug, CONCEPT_TYPE_NODE_ALIAS, {
            resourceinstance: props.resourceInstanceId,
            aliased_data: {
                [CONCEPT_TYPE_NODE_ALIAS]: newValue,
            },
            tileid: props.conceptTypeTile?.tileid,
        });

        await resourceStore.refreshResource();

        toast.add({
            severity: SUCCESS,
            summary: $gettext("Concept type updated"),
            life: DEFAULT_TOAST_LIFE,
        });

        refreshSchemeHierarchy!();
        refreshReportSection!("HierarchicalPosition");
    } catch (error) {
        toast.add({
            severity: ERROR,
            summary: $gettext("Failed to update concept type"),
            detail: error instanceof Error ? error.message : undefined,
            life: DEFAULT_ERROR_TOAST_LIFE,
        });
    }
}

function confirmDelete() {
    if (!props.concept?.resourceinstanceid) return;
    dialogMode.value = DELETE;
    showDeleteDialog.value = true;
}

function confirmDeprecate() {
    if (!props.concept?.resourceinstanceid) return;
    dialogMode.value = DEPRECATE;
    showDeleteDialog.value = true;
}

async function onDeleteConfirmed(strategy: DeleteConceptStrategy | null) {
    showDeleteDialog.value = false;
    if (!props.concept) return;

    const schemeIdentifier =
        props.concept.aliased_data?.part_of_scheme?.aliased_data.part_of_scheme
            ?.node_value?.[0]?.resourceId;

    try {
        await deleteConcept(
            props.concept.resourceinstanceid,
            strategy ?? undefined,
        );
        router.push({
            name: routeNames.scheme,
            params: { id: schemeIdentifier },
            query: router.currentRoute.value.query,
        });
        refreshSchemeHierarchy!();
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Error deleting concept"),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

async function onDeprecateConfirmed(strategy: DeleteConceptStrategy | null) {
    showDeleteDialog.value = false;
    if (!props.concept) return;

    try {
        await retireConcept(
            props.concept.resourceinstanceid,
            strategy ?? undefined,
        );
        router.push({
            name: routeNames.concept,
            params: { id: props.concept.resourceinstanceid },
            query: router.currentRoute.value.query,
        });
        refreshSchemeHierarchy!();
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Error deprecating concept"),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

function onConfirmed(strategy: DeleteConceptStrategy | null) {
    if (dialogMode.value === DELETE) {
        onDeleteConfirmed(strategy);
    } else {
        onDeprecateConfirmed(strategy);
    }
}

function openExportDialog() {
    exportDialogKey.value++;
    showExportDialog.value = true;
}

function addChild() {
    const schemeId =
        props.concept?.aliased_data?.part_of_scheme?.aliased_data
            ?.part_of_scheme?.node_value?.[0]?.resourceId;
    const parentId = props.resourceInstanceId;

    if (!schemeId || !parentId) return;

    navigateToSchemeOrConcept(router, NEW_CONCEPT, {
        scheme: schemeId,
        parent: parentId,
    });
}
</script>

<template>
    <DeleteConceptDialog
        v-if="concept && showDeleteDialog"
        :concept-id="concept.resourceinstanceid"
        :concept-name="label?.value"
        :mode="dialogMode"
        @confirm="onConfirmed"
        @cancel="showDeleteDialog = false"
    />
    <ExportThesauri
        v-if="concept && showExportDialog"
        :key="exportDialogKey"
        :resource-id="concept.resourceinstanceid"
        :resource-name="label?.value"
    />
    <div class="concept-header-toolbar">
        <div class="concept-details">
            <div class="concept-header-title">
                <div class="concept-name">
                    <i :class="conceptIcon"></i>
                    <span>
                        {{ label?.value }}
                        <span
                            v-if="label?.language_id"
                            class="concept-label-lang"
                        >
                            ({{ label?.language_id }})
                        </span>
                    </span>
                </div>
            </div>
            <div class="card flex justify-center">
                <GenericWidget
                    v-if="concept && concept.resourceinstanceid"
                    :node-alias="CONCEPT_TYPE_NODE_ALIAS"
                    :graph-slug="graphSlug"
                    :mode="isEditor ? EDIT : VIEW"
                    :aliased-node-data="
                        conceptTypeTile?.aliased_data?.[CONCEPT_TYPE_NODE_ALIAS]
                    "
                    :should-show-label="false"
                    class="concept-type-widget"
                    @update:value="onConceptTypeChange"
                />
            </div>
        </div>
        <div
            v-if="resourceInstanceId"
            class="header-buttons"
        >
            <Button
                :aria-label="$gettext('Edit History')"
                class="add-button"
                @click="openEditLog"
            >
                <span><i class="pi pi-history"></i></span>
                <span>{{ $gettext("History") }}</span>
            </Button>
            <Button
                :aria-label="$gettext('Export')"
                class="add-button"
                @click="openExportDialog"
            >
                <span><i class="pi pi-cloud-download"></i></span>
                <span>{{ $gettext("Export") }}</span>
            </Button>
            <Button
                v-if="canEditResourceInstances"
                icon="pi pi-plus-circle"
                :label="$gettext('Add Child')"
                class="add-button"
                @click="addChild"
            />
            <Button
                v-if="canDelete"
                icon="pi pi-trash"
                :severity="DANGER"
                class="delete-button"
                :label="$gettext('Delete')"
                :aria-label="$gettext('Delete Concept')"
                @click="confirmDelete"
            />
            <Button
                v-if="canDeprecate"
                icon="pi pi-ban"
                :severity="DANGER"
                class="delete-button"
                :label="$gettext('Deprecate')"
                :aria-label="$gettext('Deprecate Concept')"
                @click="confirmDeprecate"
            />
        </div>
    </div>
</template>

<style scoped>
.concept-header-toolbar {
    min-height: 3rem;
    height: auto;
    background: var(--p-header-toolbar-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    row-gap: 0.5rem;
    padding-inline-start: 1rem;
    padding-inline-end: 1rem;
    padding-top: 0.375rem;
    padding-bottom: 0.375rem;
    box-sizing: border-box;
}

.concept-details {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
}

.concept-name {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    min-width: 0;
}

.concept-name > span {
    min-width: 0;
    white-space: normal;
    overflow: visible;
    text-overflow: clip;
    overflow-wrap: anywhere;
    word-break: break-word;
}

.p-select {
    margin: 0rem 0.5rem;
    border-radius: 0.125rem;
    box-shadow: none;
    width: auto;
    max-width: 100%;
    min-width: 0;
}

:deep(.p-select-label) {
    font-size: 0.875rem !important;
}

.concept-header-title {
    margin-top: 0;
    margin-bottom: 0;
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
    min-width: 0;
}

.delete-button {
    font-size: var(--p-lingo-font-size-small);
}

.header-buttons {
    display: flex;
    gap: 0.25rem;
    flex-wrap: wrap;
    justify-content: flex-end;
    min-width: 0;
}

.concept-label-lang {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
}

:deep(.p-selectbutton) {
    border-radius: 0.125rem;
}

:deep(.p-togglebutton-checked .p-togglebutton-content) {
    border-radius: 0.125rem;
}

:deep(.p-selectbutton .p-togglebutton:first-child) {
    border-radius: 0.125rem;
}

:deep(.concept-type-widget .p-icon.p-treeselect-clear-icon) {
    display: none;
}
</style>
