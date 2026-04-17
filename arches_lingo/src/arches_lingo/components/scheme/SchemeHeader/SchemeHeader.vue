<script setup lang="ts">
import { computed, inject, onMounted, ref, watch } from "vue";
import { useGettext } from "vue3-gettext";

import { useEditLog } from "@/arches_lingo/composables/useEditLog.ts";

import { useConfirm } from "primevue/useconfirm";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import { storeToRefs } from "pinia";

import Skeleton from "primevue/skeleton";
import ConfirmDialog from "primevue/confirmdialog";
import Dialog from "primevue/dialog";
import Button from "primevue/button";

import ExportThesauri from "@/arches_lingo/components/scheme/SchemeHeader/components/ExportThesauri.vue";
import LifecycleButtons from "@/arches_lingo/components/scheme/SchemeHeader/components/LifecycleButtons.vue";
import ReinstateDialog from "@/arches_lingo/components/generic/ReinstateDialog.vue";
import SchemeIdentifierField from "@/arches_lingo/components/scheme/SchemeHeader/components/SchemeIdentifierField.vue";
import SchemeURITemplateField from "@/arches_lingo/components/scheme/SchemeHeader/components/SchemeURITemplateField.vue";
import ConceptIdentifierCounterField from "@/arches_lingo/components/scheme/SchemeHeader/components/ConceptIdentifierCounterField.vue";
import LifecycleStateBadge from "@/arches_lingo/components/generic/LifecycleStateBadge.vue";

import {
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    NEW_CONCEPT,
    SECONDARY,
} from "@/arches_lingo/constants.ts";
import { PREF_LABEL } from "@/arches_controlled_lists/constants.ts";

import {
    deleteLingoResource,
    fetchSchemeResource,
    fetchResourceIdentifiers,
    fetchConceptIdentifierCounter,
    fetchSchemeURITemplate,
    fetchResourceInstanceLifecycleState,
    fetchSchemeLabelCounts,
    unretireSchemeConcepts,
} from "@/arches_lingo/api.ts";
import { useResourceStore } from "@/arches_lingo/composables/useResourceStore.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";
import { useAppSettingsStore } from "@/arches_lingo/stores/useAppSettingsStore.ts";
import {
    extractDescriptors,
    navigateToSchemeOrConcept,
} from "@/arches_lingo/utils.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

import type {
    DataComponentMode,
    LanguageLabelCount,
    ResourceInstanceResult,
    SchemeHeader,
    ResourceInstanceLifecycleState,
} from "@/arches_lingo/types.ts";
import type { Label, Labellable } from "@/arches_controlled_lists/types";
import { routeNames } from "@/arches_lingo/routes.ts";

type ConceptIdentifierCounter = {
    scheme_resource_instance_id: string;
    start_number: number;
    next_number: number;
};

type SchemeURITemplate = {
    scheme_resource_instance_id: string;
    url_template: string;
};

const props = defineProps<{
    mode: DataComponentMode;
    sectionTitle: string;
    componentName: string;
    graphSlug: string;
    resourceInstanceId: string | undefined;
    nodegroupAlias: string;
}>();

const refreshSchemeHierarchy = inject<() => void>("refreshSchemeHierarchy");
const { openEditLog } = useEditLog(() => props.graphSlug);

const confirm = useConfirm();
const router = useRouter();
const toast = useToast();
const { $gettext, interpolate } = useGettext();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

const scheme = ref<ResourceInstanceResult>();
const schemeResource = ref<Labellable>();
const label = ref<Label>();
const data = ref<SchemeHeader>();
const labelCounts = ref<LanguageLabelCount[]>([]);
const labelCountsLoading = ref(false);
const showAllLanguages = ref(false);

const LANGUAGE_CHIPS_TRUNCATE_COUNT = 8;

const visibleLabelCounts = computed(() => {
    if (showAllLanguages.value) return labelCounts.value;
    return labelCounts.value.slice(0, LANGUAGE_CHIPS_TRUNCATE_COUNT);
});

const hiddenLanguageCount = computed(
    () => labelCounts.value.length - LANGUAGE_CHIPS_TRUNCATE_COUNT,
);

const visibleLabelChips = computed(() =>
    visibleLabelCounts.value.map((entry) => ({
        key: entry.code,
        label: interpolate(
            $gettext("%{language} (%{code}): %{count}"),
            { language: entry.language, code: entry.code, count: entry.count },
            true,
        ),
    })),
);

const showMoreLabel = computed(() =>
    interpolate($gettext("+%{count} more"), {
        count: hiddenLanguageCount.value,
    }),
);

const isLoading = ref(true);
const showExportDialog = ref(false);
const exportDialogKey = ref(0);
const showReinstateDialog = ref(false);
const showRetireDialog = ref(false);
const isReinstateLoading = ref(false);
const pendingReinstateStateId = ref<string | undefined>();
const pendingRetireStateId = ref<string | undefined>();
const lifecycleButtonsRef = ref<InstanceType<typeof LifecycleButtons> | null>(
    null,
);
const identifierValue = ref<string>();

const resourceIdentifierId = ref<number | undefined>();

const conceptIdentifierCounter = ref<ConceptIdentifierCounter | undefined>();

const schemeURITemplate = ref<SchemeURITemplate | undefined>();

const currentLifecycleState = ref<ResourceInstanceLifecycleState | undefined>();

const hasPersistedResourceInstance = computed(() => {
    return Boolean(props.resourceInstanceId);
});

const store = useResourceStore();
const { isEditor } = useUserStore();
const { publicServerAddress } = storeToRefs(useAppSettingsStore());

watch(
    [() => store.resource.value, () => store.error.value],
    async ([resource, storeError]) => {
        if (storeError) {
            toast.add({
                severity: ERROR,
                life: DEFAULT_ERROR_TOAST_LIFE,
                summary: $gettext("Unable to fetch scheme"),
                detail: storeError.message,
            });
            isLoading.value = false;
            return;
        }
        if (!resource || !props.resourceInstanceId) return;

        try {
            scheme.value = resource;

            const schemeResource = await fetchSchemeResource(
                props.resourceInstanceId,
            );

            label.value = getItemLabel(
                schemeResource,
                selectedLanguage.value.code,
                systemLanguage.value.code,
            );

            extractSchemeHeaderData(resource);

            labelCountsLoading.value = true;
            fetchSchemeLabelCounts(props.resourceInstanceId)
                .then((counts) => {
                    labelCounts.value = counts;
                })
                .finally(() => {
                    labelCountsLoading.value = false;
                });
        } catch (error) {
            toast.add({
                severity: ERROR,
                life: DEFAULT_ERROR_TOAST_LIFE,
                summary: $gettext("Unable to fetch scheme"),
                detail: error instanceof Error ? error.message : undefined,
            });
        } finally {
            isLoading.value = false;
        }
    },
    { immediate: true },
);

const canEditResourceInstances = computed(() => {
    return (
        isEditor &&
        hasPersistedResourceInstance.value &&
        Boolean(currentLifecycleState.value?.can_edit_resource_instances)
    );
});

const canDeleteResourceInstances = computed(() => {
    return (
        isEditor &&
        hasPersistedResourceInstance.value &&
        Boolean(currentLifecycleState.value?.can_delete_resource_instances)
    );
});

const canAddTopConcept = computed(() => {
    return canEditResourceInstances.value;
});

const defaultSchemeURITemplate = computed(() => {
    const baseUrl = publicServerAddress.value?.trim();
    if (!baseUrl) {
        return undefined;
    }

    const normalizedBaseUrl = baseUrl.replace(/\/+$/, "");
    return `${normalizedBaseUrl}/scheme/<scheme_identifier>/concept/<concept_identifier>`;
});

const schemeUri = computed(() => {
    return scheme.value?.aliased_data?.uri?.aliased_data?.uri_content
        ?.node_value;
});

onMounted(async () => {
    if (!props.resourceInstanceId) {
        label.value = {
            value: $gettext("New Scheme"),
            language_id: selectedLanguage.value.code,
            valuetype_id: PREF_LABEL,
        };
        isLoading.value = false;
        return;
    }

    try {
        const resourceInstanceId = props.resourceInstanceId;

        const [
            fetchedResourceIdentifiers,
            fetchedConceptIdentifierCounter,
            fetchedSchemeURITemplate,
            fetchedLifecycleState,
        ] = await Promise.all([
            fetchResourceIdentifiers(resourceInstanceId),
            fetchConceptIdentifierCounter(resourceInstanceId).catch(
                () => undefined,
            ),
            fetchSchemeURITemplate(resourceInstanceId).catch(() => undefined),
            fetchResourceInstanceLifecycleState(resourceInstanceId),
        ]);

        identifierValue.value = fetchedResourceIdentifiers?.[0]?.identifier;
        resourceIdentifierId.value = fetchedResourceIdentifiers?.[0]?.id;

        conceptIdentifierCounter.value = fetchedConceptIdentifierCounter;
        schemeURITemplate.value = fetchedSchemeURITemplate;

        currentLifecycleState.value =
            fetchedLifecycleState as ResourceInstanceLifecycleState;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch scheme"),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
    // Resource data is loaded via the store watch above
});

function openExportDialog() {
    exportDialogKey.value++;
    showExportDialog.value = true;
}

function addTopConcept() {
    const schemeId = props.resourceInstanceId;
    if (!schemeId) {
        return;
    }
    navigateToSchemeOrConcept(router, NEW_CONCEPT, {
        scheme: schemeId,
        parent: schemeId,
    });
}

function extractSchemeHeaderData(scheme: ResourceInstanceResult) {
    const name = scheme?.name;
    const descriptor = extractDescriptors(scheme, selectedLanguage.value);
    const principalUser = scheme?.principal_user_display_name ?? undefined;

    data.value = {
        name: name,
        descriptor: descriptor,
        principalUser: principalUser,
        lifeCycleState: currentLifecycleState.value?.name || "--",
    };
}

watch(
    () => selectedLanguage.value.code,
    (newCode) => {
        if (schemeResource.value) {
            label.value = getItemLabel(
                schemeResource.value,
                newCode,
                systemLanguage.value.code,
            );
        }
        if (scheme.value) {
            extractSchemeHeaderData(scheme.value);
        }
    },
);

function onIdentifierUpdate(updatedIdentifier: {
    identifierValue: string | undefined;
    resourceIdentifierId: number | undefined;
}) {
    identifierValue.value = updatedIdentifier.identifierValue;
    resourceIdentifierId.value = updatedIdentifier.resourceIdentifierId;
}

function onSchemeURITemplateUpdate(updatedTemplate: {
    schemeURITemplate: SchemeURITemplate | undefined;
}) {
    schemeURITemplate.value = updatedTemplate.schemeURITemplate;
}

function onConceptIdentifierCounterUpdate(updatedCounter: {
    conceptIdentifierCounter: ConceptIdentifierCounter | undefined;
}) {
    conceptIdentifierCounter.value = updatedCounter.conceptIdentifierCounter;
}

function confirmDelete() {
    confirm.require({
        header: $gettext("Confirmation"),
        message: $gettext("Are you sure you want to delete this scheme?"),
        group: "delete-scheme",
        accept: () => {
            if (!scheme.value) {
                return;
            }

            try {
                deleteLingoResource(
                    props.graphSlug,
                    scheme.value.resourceinstanceid,
                ).then(() => {
                    router.push({
                        name: routeNames.schemes,
                    });

                    refreshSchemeHierarchy!();
                });
            } catch (error) {
                toast.add({
                    severity: ERROR,
                    life: DEFAULT_ERROR_TOAST_LIFE,
                    summary: $gettext("Error deleting scheme"),
                    detail: error instanceof Error ? error.message : undefined,
                });
            }
        },
        rejectProps: {
            label: $gettext("Cancel"),
            severity: SECONDARY,
            outlined: true,
        },
        acceptProps: {
            label: $gettext("Delete"),
            severity: DANGER,
        },
    });
}

function onLifecycleStateChange(
    nextLifecycleState: ResourceInstanceLifecycleState,
) {
    currentLifecycleState.value = nextLifecycleState;

    if (data.value) {
        data.value.lifeCycleState = nextLifecycleState.name;
    }

    window.location.reload();
}

function onRetireRequested(nextStateId: string) {
    pendingRetireStateId.value = nextStateId;
    showRetireDialog.value = true;
}

function onRetireConfirmed() {
    if (!pendingRetireStateId.value) return;
    lifecycleButtonsRef.value?.transitionLifecycleState(
        pendingRetireStateId.value,
    );
    showRetireDialog.value = false;
    pendingRetireStateId.value = undefined;
}

function onReinstateRequested(nextStateId: string) {
    pendingReinstateStateId.value = nextStateId;
    showReinstateDialog.value = true;
}

async function onReinstateConfirmed(cascade: boolean) {
    if (!props.resourceInstanceId || !pendingReinstateStateId.value) {
        return;
    }

    isReinstateLoading.value = true;
    try {
        if (cascade) {
            await unretireSchemeConcepts(props.resourceInstanceId);
        }
        lifecycleButtonsRef.value?.transitionLifecycleState(
            pendingReinstateStateId.value,
        );
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Error reinstating scheme"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isReinstateLoading.value = false;
        showReinstateDialog.value = false;
        pendingReinstateStateId.value = undefined;
    }
}
</script>

<template>
    <ConfirmDialog group="delete-scheme" />
    <Dialog
        v-if="showRetireDialog"
        :visible="true"
        :modal="true"
        :dismissable-mask="false"
        :header="$gettext('Confirmation')"
        @update:visible="showRetireDialog = false"
    >
        <p>
            {{
                $gettext(
                    "Are you sure you want to retire this vocabulary? All concepts within it will also be retired.",
                )
            }}
        </p>
        <template #footer>
            <Button
                :label="$gettext('Cancel')"
                :severity="SECONDARY"
                :outlined="true"
                @click="showRetireDialog = false"
            />
            <Button
                :label="$gettext('Retire')"
                :severity="DANGER"
                @click="onRetireConfirmed"
            />
        </template>
    </Dialog>
    <ReinstateDialog
        v-if="showReinstateDialog && resourceInstanceId"
        :resource-id="resourceInstanceId"
        :resource-name="label?.value"
        resource-type="scheme"
        :is-loading="isReinstateLoading"
        @confirm="onReinstateConfirmed"
        @cancel="showReinstateDialog = false"
    />
    <ExportThesauri
        v-if="scheme && showExportDialog"
        :key="exportDialogKey"
        :resource-id="scheme.resourceinstanceid"
        :resource-name="label?.value"
    />
    <Skeleton
        v-if="isLoading"
        style="width: 100%; height: 9rem"
    />

    <div
        v-else
        class="scheme-header"
    >
        <div class="scheme-header-panel">
            <div class="scheme-header-toolbar">
                <div class="header-row">
                    <div class="scheme-title">
                        <h2>
                            <span class="scheme-title-text">{{
                                label?.value
                            }}</span>
                            <span
                                v-if="label?.language_id"
                                class="scheme-label-lang"
                            >
                                ({{ label?.language_id }})
                            </span>
                        </h2>
                    </div>

                    <div
                        v-if="props?.resourceInstanceId !== undefined"
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
                            v-if="canAddTopConcept"
                            icon="pi pi-plus-circle"
                            :label="$gettext('Add Top Concept')"
                            class="add-button"
                            @click="addTopConcept"
                        />

                        <Button
                            v-if="canDeleteResourceInstances"
                            icon="pi pi-trash"
                            severity="danger"
                            class="delete-button"
                            :label="$gettext('Delete')"
                            :aria-label="$gettext('Delete Concept')"
                            @click="confirmDelete"
                        />

                        <LifecycleButtons
                            v-if="isEditor"
                            ref="lifecycleButtonsRef"
                            :resource-instance-id="props.resourceInstanceId"
                            @change="onLifecycleStateChange"
                            @retire-requested="onRetireRequested"
                            @reinstate-requested="onReinstateRequested"
                        />
                    </div>
                </div>
            </div>

            <div class="header-content">
                <div class="header-row">
                    <SchemeIdentifierField
                        :resource-instance-id="props.resourceInstanceId"
                        :identifier-value="identifierValue"
                        :resource-identifier-id="resourceIdentifierId"
                        :can-edit-resource-instances="canEditResourceInstances"
                        @update="onIdentifierUpdate"
                    />
                    <div>
                        <span class="header-item-label">{{
                            $gettext("URI: ")
                        }}</span>
                        <Button
                            v-if="schemeUri"
                            :label="schemeUri"
                            class="concept-uri"
                            variant="link"
                            as="a"
                            :href="schemeUri"
                            target="_blank"
                            rel="noopener"
                            :disabled="!data?.uri"
                        ></Button>
                        <span
                            v-else
                            class="header-item-value"
                            >{{ $gettext("No URI assigned") }}</span
                        >
                    </div>
                </div>

                <div class="header-row">
                    <SchemeURITemplateField
                        :resource-instance-id="props.resourceInstanceId"
                        :can-edit-resource-instances="canEditResourceInstances"
                        :scheme-u-r-i-template="schemeURITemplate"
                        :default-scheme-u-r-i-template="
                            defaultSchemeURITemplate
                        "
                        @update="onSchemeURITemplateUpdate"
                    />
                </div>

                <div class="header-row">
                    <ConceptIdentifierCounterField
                        :resource-instance-id="props.resourceInstanceId"
                        :can-edit-resource-instances="canEditResourceInstances"
                        :concept-identifier-counter="conceptIdentifierCounter"
                        @update="onConceptIdentifierCounterUpdate"
                    />
                </div>

                <div class="header-row metadata-container">
                    <div class="language-chip-wrapper">
                        <div class="language-section-header">
                            <span class="header-item-label">{{
                                $gettext("Languages:")
                            }}</span>
                            <Button
                                v-if="hiddenLanguageCount > 0"
                                text
                                size="small"
                                class="language-expand-toggle"
                                :aria-expanded="showAllLanguages"
                                @click="showAllLanguages = !showAllLanguages"
                            >
                                <i
                                    :class="
                                        showAllLanguages
                                            ? 'pi pi-chevron-up'
                                            : 'pi pi-chevron-down'
                                    "
                                ></i>
                                <span>{{
                                    showAllLanguages
                                        ? $gettext("Show less")
                                        : showMoreLabel
                                }}</span>
                            </Button>
                        </div>
                        <div
                            class="language-chip-container"
                            :class="{
                                'language-chip-container--expanded':
                                    showAllLanguages,
                            }"
                        >
                            <Skeleton
                                v-if="labelCountsLoading"
                                width="12rem"
                                height="2rem"
                            />
                            <span
                                v-for="chip in visibleLabelChips"
                                v-else
                                :key="chip.key"
                                class="scheme-language"
                            >
                                {{ chip.label }}
                            </span>
                        </div>
                    </div>

                    <div class="lifecycle-container">
                        <div class="header-item">
                            <span class="header-item-label">
                                {{ $gettext("Life cycle state:") }}
                            </span>
                            <span class="header-item-value">
                                <LifecycleStateBadge
                                    :lifecycle-state-id="
                                        currentLifecycleState?.id
                                    "
                                    :lifecycle-state-name="
                                        currentLifecycleState?.name
                                    "
                                />
                                <span v-if="!currentLifecycleState">--</span>
                            </span>
                        </div>
                        <div class="header-item">
                            <span class="header-item-label">
                                {{ $gettext("Owner:") }}
                            </span>
                            <span class="header-item-value">
                                {{
                                    data?.principalUser || $gettext("Anonymous")
                                }}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.scheme-header {
    background: var(--p-header-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    box-sizing: border-box;
}

.scheme-header-panel {
    box-sizing: border-box;
}

.scheme-header-toolbar {
    min-height: 3rem;
    height: auto;
    background: var(--p-header-toolbar-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    padding-inline-start: 1rem;
    padding-inline-end: 1rem;
    padding-top: 0.375rem;
    padding-bottom: 0.375rem;
    box-sizing: border-box;
}

.scheme-title {
    min-width: 0;
}

.scheme-title-text {
    min-width: 0;
    white-space: normal;
    overflow: visible;
    text-overflow: clip;
    overflow-wrap: anywhere;
    word-break: break-word;
}

h2 {
    margin-top: 0;
    margin-bottom: 0;
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
    min-width: 0;
}

h2 > span {
    min-width: 0;
}

.scheme-label-lang {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
    vertical-align: baseline;
}

.header-content {
    min-height: 5.45rem;
    padding-top: 0.5rem;
    padding-inline-start: 1rem;
    padding-inline-end: 1rem;
    box-sizing: border-box;
}

.header-buttons {
    display: flex;
    gap: 0.25rem;
    flex-wrap: wrap;
    justify-content: flex-end;
    min-width: 0;
}

.delete-button {
    font-size: var(--p-lingo-font-size-small);
}

.p-button-link {
    padding: 0;
    margin: 0;
}

.header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    column-gap: 1rem;
    row-gap: 0.5rem;
    padding: 0.2rem 0 0 0;
    min-width: 0;
}

.metadata-container {
    gap: 0.75rem;
    margin-top: 0;
    padding-bottom: 1rem;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: nowrap;
}

.language-chip-container {
    display: flex;
    gap: 0.25rem;
    align-items: center;
    flex-wrap: wrap;
    min-width: 0;
}

.language-chip-wrapper {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 0;
    flex: 1 1 0;
}

.language-section-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.language-chip-container--expanded {
    align-items: flex-start;
    align-content: flex-start;
}

.language-expand-toggle {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.125rem 0.375rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-primary-500);
    background: none;
    border: 0;
    cursor: pointer;
    font-family: inherit;
    line-height: 1.4;
}

.language-expand-toggle:hover {
    color: var(--p-primary-600);
    background: var(--p-primary-50);
}

.language-expand-toggle .pi {
    font-size: 0.6rem;
}

.add-language:hover {
    cursor: pointer;
}

.lifecycle-container {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    flex-shrink: 0;
}

.add-language {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-primary-500);
    text-decoration: underline;
    padding: 0 0.5rem;
}

.header-item {
    display: inline-flex;
    align-items: center;
    min-width: 0;
}

.header-item-label {
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
    margin-inline-end: 0.25rem;
}

.header-item-value {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-primary-500);
    min-width: 0;
}

:deep(.header-item) {
    display: inline-flex;
    align-items: center;
    min-width: 0;
}

:deep(.header-item-label) {
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
    margin-inline-end: 0.25rem;
}

:deep(.header-item-value) {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-primary-500);
    min-width: 0;
}

:deep(.identifier-item) {
    min-width: 0;
}

:deep(.identifier-value) {
    min-width: 0;
}

.scheme-language {
    padding: 0.5rem 1rem;
    background: var(--p-menubar-item-icon-color);
    border: 0.0625rem solid var(--p-menubar-item-icon-color);
    border-radius: 0.125rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-content-color);
}

.export-panel {
    padding: 1rem;
}

.exports-panel-container {
    font-family: var(--p-lingo-font-family);
    font-weight: 300;
    padding: 0 1rem;
}

.options-container {
    padding: 0 0 0.75rem 0;
}

.options-container h4 {
    margin: 0;
    padding-bottom: 0.4rem;
}

.formats-container {
    padding: 0 0 0.75rem 0;
}

.formats-container h4 {
    margin: 0;
}

.selection {
    display: flex;
    gap: 0.5rem;
    padding: 0.2rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    align-items: center;
    color: var(--p-list-option-icon-color);
}

.export-footer {
    display: flex;
    flex-direction: row-reverse;
    gap: 0.25rem;
    border-top: 0.0625rem solid var(--p-header-toolbar-border);
    padding: 0.5rem 0 0 0;
}

.container-title {
    font-size: var(--p-lingo-font-size-normal);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    margin-bottom: 0.5rem;
}

.container-title h3 {
    padding-top: 0.5rem;
    margin: 0rem 0rem 0.25rem 0rem;
    font-weight: var(--p-lingo-font-weight-normal);
}

.concept-label-lang {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
}
</style>
