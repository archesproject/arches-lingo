<script setup lang="ts">
import { computed, inject, ref, watch } from "vue";

import { useGettext } from "vue3-gettext";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import { storeToRefs } from "pinia";

import Button from "primevue/button";
import Tag from "primevue/tag";

import GenericWidget from "@/arches_vue_components/generics/GenericWidget/GenericWidget.vue";

import ConceptMergeDialog from "@/arches_lingo/components/concept/ConceptMerge/ConceptMergeDialog.vue";
import DeleteConceptDialog from "@/arches_lingo/components/concept/ConceptHeader/components/DeleteConceptDialog.vue";
import ExportThesauri from "@/arches_lingo/components/scheme/SchemeHeader/components/ExportThesauri.vue";
import LifecycleButtons from "@/arches_lingo/components/scheme/SchemeHeader/components/LifecycleButtons.vue";
import ReinstateDialog from "@/arches_lingo/components/generic/ReinstateDialog.vue";

import {
    deleteConcept,
    retireConcept,
    unretireConcept,
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
    HIERARCHY_NAME_ICON,
    HIERARCHY_NAME_URI,
    LOCKED_LIFECYCLE_STATE_ID,
    NEW_CONCEPT,
    PUBLISHED_LIFECYCLE_STATE_ID,
    RETIRED_LIFECYCLE_STATE_ID,
    SUCCESS,
    TOP_CONCEPT_ICON,
} from "@/arches_lingo/constants.ts";

import { routeNames } from "@/arches_lingo/routes.ts";
import { navigateToSchemeOrConcept } from "@/arches_lingo/utils.ts";

import { useDialogFocusReturn } from "@/arches_lingo/composables/useDialogFocusReturn.ts";
import { useEditLog } from "@/arches_lingo/composables/useEditLog.ts";
import { setPageTitleDetail } from "@/arches_lingo/composables/usePageTitle.ts";
import { useResourceStore } from "@/arches_lingo/composables/useResourceStore.ts";
import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

import type { Ref } from "vue";
import type { AliasedNodeData } from "@/arches_vue_components/types.ts";
import type {
    DeleteConceptStrategy,
    ResourceInstanceLifecycleState,
    ResourceInstanceResult,
} from "@/arches_lingo/types.ts";
import type { Label } from "@/arches_controlled_lists/types.ts";
import type { ReferenceSelectValue } from "@/arches_controlled_lists/datatypes/reference-select/types.ts";

const emit = defineEmits<{
    (event: "update:isWidgetLoading", isWidgetLoading: boolean): void;
}>();

const props = defineProps<{
    concept: ResourceInstanceResult | undefined;
    label: Label | undefined;
    graphSlug: string;
    resourceInstanceId: string | undefined;
    conceptTypeTile:
        | {
              tileid?: string;
              aliased_data?: Record<string, AliasedNodeData>;
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
const conceptStore = useConceptStore();

const { openEditLog } = useEditLog(() => props.graphSlug);

watch(() => props.label?.value, setPageTitleDetail, { immediate: true });

const lifecycleButtonsRef = ref<InstanceType<typeof LifecycleButtons> | null>(
    null,
);

const conceptNameHeadingRef = ref<HTMLElement | null>(null);

function getConceptNameHeading() {
    return conceptNameHeadingRef.value;
}

const showExportDialog = ref(false);
const exportDialogKey = ref(0);
const {
    isDialogMounted: isDeleteDialogMounted,
    isDialogVisible: isDeleteDialogVisible,
    openDialog: openDeleteDialog,
    closeDialog: closeDeleteDialog,
    onDialogAfterHide: onDeleteDialogAfterHide,
} = useDialogFocusReturn(getConceptNameHeading);
const {
    isDialogMounted: isReinstateDialogMounted,
    isDialogVisible: isReinstateDialogVisible,
    openDialog: openReinstateDialog,
    closeDialog: closeReinstateDialog,
    onDialogAfterHide: onReinstateDialogAfterHide,
} = useDialogFocusReturn(getConceptNameHeading);
const {
    isDialogMounted: isMergeDialogMounted,
    isDialogVisible: isMergeDialogVisible,
    openDialog: openMergeDialog,
    closeDialog: closeMergeDialog,
    onDialogAfterHide: onMergeDialogAfterHide,
} = useDialogFocusReturn(getConceptNameHeading);
const isLoading = ref(false);
const isWidgetLoading = ref(false);
const dialogMode = ref<typeof DELETE | typeof DEPRECATE>(DELETE);

watch(isWidgetLoading, (newValue) => {
    emit("update:isWidgetLoading", newValue);
});

const lifecycleState = computed(function () {
    return resourceInstanceLifecycleState?.value;
});

const conceptTypeLabel = computed(function () {
    const aliasedData =
        props.conceptTypeTile?.aliased_data?.[CONCEPT_TYPE_NODE_ALIAS];
    return (aliasedData as { display_value?: string } | undefined)
        ?.display_value;
});

const conceptIcon = computed(function () {
    const typeNodeValue =
        props.conceptTypeTile?.aliased_data?.[CONCEPT_TYPE_NODE_ALIAS]
            ?.node_value;
    if (isGuideTermType(typeNodeValue)) return GUIDE_TERM_ICON;
    if (isHierarchyNameType(typeNodeValue)) return HIERARCHY_NAME_ICON;
    if (props.isTopConcept) return TOP_CONCEPT_ICON;
    return CONCEPT_ICON;
});

const canEditResourceInstances = computed(function () {
    return (
        isEditor.value === true &&
        !isSchemeLocked.value &&
        props.resourceInstanceId !== undefined &&
        lifecycleState.value?.can_edit_resource_instances === true
    );
});

const canMerge = computed(function () {
    return canEditResourceInstances.value && Boolean(schemeId.value);
});

const canDelete = computed(function () {
    if (!isEditor.value || isSchemeLocked.value || !props.resourceInstanceId)
        return false;
    return lifecycleState.value?.can_delete_resource_instances === true;
});

const schemeId = computed(function () {
    return props.concept?.aliased_data?.part_of_scheme?.aliased_data
        ?.part_of_scheme?.node_value?.[0]?.resourceId;
});

const isSchemeRetired = computed(function () {
    if (!schemeId.value) return false;
    const scheme = conceptStore.schemes.find(
        (candidate) => candidate.id === schemeId.value,
    );
    return (
        scheme?.resource_instance_lifecycle_state_id ===
        RETIRED_LIFECYCLE_STATE_ID
    );
});

const isSchemePublished = computed(function () {
    if (!schemeId.value) return false;
    const scheme = conceptStore.schemes.find(
        (candidate) => candidate.id === schemeId.value,
    );
    return (
        scheme?.resource_instance_lifecycle_state_id ===
        PUBLISHED_LIFECYCLE_STATE_ID
    );
});

const isSchemeLocked = computed(function () {
    if (!schemeId.value) return false;
    const scheme = conceptStore.schemes.find(
        (candidate) => candidate.id === schemeId.value,
    );
    return (
        scheme?.resource_instance_lifecycle_state_id ===
        LOCKED_LIFECYCLE_STATE_ID
    );
});

const showLifecycleButtons = computed(function () {
    return (
        isEditor.value &&
        !isSchemeLocked.value &&
        !isSchemeRetired.value &&
        !isSchemePublished.value
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

function isHierarchyNameType(typeNodeValue: unknown): boolean {
    if (!Array.isArray(typeNodeValue) || typeNodeValue.length === 0) {
        return false;
    }
    return typeNodeValue.some(
        (typeRef: { uri?: string }) => typeRef.uri === HIERARCHY_NAME_URI,
    );
}

async function onConceptTypeChange(newValue: unknown) {
    const conceptTypeValue = newValue as ReferenceSelectValue;

    try {
        await upsertLingoTile(props.graphSlug, CONCEPT_TYPE_NODE_ALIAS, {
            resourceinstance: props.resourceInstanceId,
            aliased_data: {
                [CONCEPT_TYPE_NODE_ALIAS]: conceptTypeValue,
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
    openDeleteDialog();
}

async function onConfirmed(strategy: DeleteConceptStrategy | null) {
    if (!props.concept) return;

    isLoading.value = true;
    try {
        if (dialogMode.value === DELETE) {
            const schemeIdentifier =
                props.concept.aliased_data?.part_of_scheme?.aliased_data
                    ?.part_of_scheme?.node_value?.[0]?.resourceId;

            await deleteConcept(
                props.concept.resourceinstanceid,
                strategy ?? undefined,
            );

            refreshSchemeHierarchy!();
            closeDeleteDialog();

            router.push({
                name: routeNames.scheme,
                params: { id: schemeIdentifier },
                query: router.currentRoute.value.query,
            });
        } else {
            await retireConcept(
                props.concept.resourceinstanceid,
                strategy ?? undefined,
            );

            refreshSchemeHierarchy!();
            closeDeleteDialog();

            lifecycleButtonsRef.value?.refreshLifecycleState();
            refreshReportSection!("all");
        }
    } catch (error) {
        let summary;
        if (dialogMode.value === DELETE) {
            summary = $gettext("Error deleting concept");
        } else {
            summary = $gettext("Error deprecating concept");
        }
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary,
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
    }
}

async function onReinstateConfirmed(cascade: boolean) {
    if (!props.concept) return;

    isLoading.value = true;
    try {
        await unretireConcept(props.concept.resourceinstanceid, cascade);
        refreshSchemeHierarchy!();
        closeReinstateDialog();
        lifecycleButtonsRef.value?.refreshLifecycleState();
        refreshReportSection!("all");
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Error reinstating concept"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
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

function onRetireRequested() {
    if (!props.concept?.resourceinstanceid) return;
    dialogMode.value = DEPRECATE;
    openDeleteDialog();
}

function onReinstateRequested() {
    openReinstateDialog();
}

async function onMerged() {
    closeMergeDialog();
    refreshSchemeHierarchy!();
    // Refreshes the resource and the lifecycle state, which every report section
    // either reads from directly or now watches for.
    await refreshReportSection!("all");

    toast.add({
        severity: SUCCESS,
        life: DEFAULT_TOAST_LIFE,
        summary: $gettext("Concepts merged"),
    });
}

function findMatches(): void {
    if (!props.concept?.resourceinstanceid) return;
    router.push({
        name: routeNames.conceptMatches,
        query: { concept: props.concept.resourceinstanceid },
    });
}

function onMergeCancelled() {
    closeMergeDialog();
}
</script>

<template>
    <DeleteConceptDialog
        v-if="concept && isDeleteDialogMounted"
        :visible="isDeleteDialogVisible"
        :concept-id="concept.resourceinstanceid"
        :concept-name="label?.value"
        :mode="dialogMode"
        :is-loading="isLoading"
        @confirm="onConfirmed"
        @cancel="closeDeleteDialog()"
        @after-hide="onDeleteDialogAfterHide"
    />
    <ConceptMergeDialog
        v-if="concept && isMergeDialogMounted && schemeId"
        :visible="isMergeDialogVisible"
        :survivor-concept="concept"
        :survivor-label="label?.value"
        :scheme-id="schemeId"
        :graph-slug="graphSlug"
        @merged="onMerged"
        @cancel="onMergeCancelled"
        @after-hide="onMergeDialogAfterHide"
    />
    <ReinstateDialog
        v-if="concept && isReinstateDialogMounted"
        :visible="isReinstateDialogVisible"
        :resource-id="concept.resourceinstanceid"
        :resource-name="label?.value"
        resource-type="concept"
        :is-loading="isLoading"
        @confirm="onReinstateConfirmed"
        @cancel="closeReinstateDialog()"
        @after-hide="onReinstateDialogAfterHide"
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
                <h1
                    ref="conceptNameHeadingRef"
                    class="concept-name"
                >
                    <i
                        :class="conceptIcon"
                        aria-hidden="true"
                    ></i>
                    <span>
                        {{ label?.value }}
                        <span
                            v-if="label?.language_id"
                            class="concept-label-lang"
                        >
                            ({{ label?.language_id }})
                        </span>
                    </span>
                </h1>
            </div>
            <div class="card flex justify-center">
                <Tag
                    v-if="conceptTypeLabel && !canEditResourceInstances"
                    :value="conceptTypeLabel"
                    severity="secondary"
                    class="concept-type-badge"
                />
                <div
                    v-else-if="concept && concept.resourceinstanceid"
                    class="concept-type-widget"
                >
                    <GenericWidget
                        :node-alias="CONCEPT_TYPE_NODE_ALIAS"
                        :graph-slug="graphSlug"
                        :mode="EDIT"
                        :aliased-node-data="
                            conceptTypeTile?.aliased_data?.[
                                CONCEPT_TYPE_NODE_ALIAS
                            ] ?? null
                        "
                        :should-show-label="false"
                        @update:is-loading="isWidgetLoading = $event"
                        @update:value="onConceptTypeChange"
                    />
                </div>
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
                <span
                    ><i
                        class="pi pi-history"
                        aria-hidden="true"
                    ></i
                ></span>
                <span>{{ $gettext("History") }}</span>
            </Button>
            <Button
                v-if="isEditor"
                :aria-label="$gettext('Export')"
                class="add-button"
                @click="openExportDialog"
            >
                <span
                    ><i
                        class="pi pi-cloud-download"
                        aria-hidden="true"
                    ></i
                ></span>
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
                v-if="isEditor && concept?.resourceinstanceid"
                icon="pi pi-clone"
                class="add-button"
                :label="$gettext('Find Matches')"
                @click="findMatches"
            />
            <Button
                v-if="canMerge"
                icon="pi pi-sign-in"
                class="add-button"
                :label="$gettext('Merge')"
                :aria-label="$gettext('Merge another concept into this one')"
                @click="openMergeDialog"
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
            <LifecycleButtons
                v-if="showLifecycleButtons"
                ref="lifecycleButtonsRef"
                :resource-instance-id="resourceInstanceId"
                :retire-reinstate-only="true"
                @retire-requested="onRetireRequested"
                @reinstate-requested="onReinstateRequested"
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
    padding-inline-end: 0.5rem;
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
    margin: 0;
    font-size: inherit;
    font-weight: inherit;
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

.concept-type-badge {
    display: inline-flex;
    align-items: center;
    line-height: 1;
    font-size: var(--p-lingo-font-size-xxsmall);
    background: var(--p-header-button-background);
    color: var(--p-header-button-color);
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    white-space: nowrap;
}
</style>
