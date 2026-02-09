<script setup lang="ts">
import { computed, inject, onMounted, ref, type Ref } from "vue";
import { useGettext } from "vue3-gettext";

import { useConfirm } from "primevue/useconfirm";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";

import Skeleton from "primevue/skeleton";
import ConfirmDialog from "primevue/confirmdialog";
import Button from "primevue/button";

import ExportThesauri from "@/arches_lingo/components/scheme/SchemeHeader/components/ExportThesauri.vue";
import LifecycleButtons from "@/arches_lingo/components/scheme/SchemeHeader/components/LifecycleButtons.vue";
import SchemeIdentifierField from "@/arches_lingo/components/scheme/SchemeHeader/components/SchemeIdentifierField.vue";
import SchemeURITemplateField from "@/arches_lingo/components/scheme/SchemeHeader/components/SchemeURITemplateField.vue";
import ConceptIdentifierCounterField from "@/arches_lingo/components/scheme/SchemeHeader/components/ConceptIdentifierCounterField.vue";

import {
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    SECONDARY,
    systemLanguageKey,
    selectedLanguageKey,
} from "@/arches_lingo/constants.ts";
import { PREF_LABEL } from "@/arches_controlled_lists/constants.ts";

import {
    deleteLingoResource,
    fetchLingoResource,
    fetchSchemeResource,
    fetchResourceIdentifiers,
    fetchConceptIdentifierCounter,
    fetchSchemeURITemplate,
    fetchPublicServerAddress,
    fetchResourceInstanceLifecycleState,
} from "@/arches_lingo/api.ts";
import { extractDescriptors } from "@/arches_lingo/utils.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";

import type {
    DataComponentMode,
    ResourceInstanceResult,
    SchemeHeader,
    ResourceInstanceLifecycleState,
} from "@/arches_lingo/types.ts";
import type { Language } from "@/arches_component_lab/types.ts";
import type { Label } from "@/arches_controlled_lists/types";
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

const confirm = useConfirm();
const router = useRouter();
const toast = useToast();
const { $gettext } = useGettext();
const systemLanguage = inject(systemLanguageKey) as Language;
const selectedLanguage = inject(selectedLanguageKey) as Ref<Language>;

const scheme = ref<ResourceInstanceResult>();
const label = ref<Label>();
const data = ref<SchemeHeader>();
const isLoading = ref(true);
const showExportDialog = ref(false);
const exportDialogKey = ref(0);
const identifierValue = ref<string>();

const resourceIdentifierId = ref<number | undefined>();

const conceptIdentifierCounter = ref<ConceptIdentifierCounter | undefined>();

const schemeURITemplate = ref<SchemeURITemplate | undefined>();

const publicServerAddress = ref<string | undefined>();

const currentLifecycleState = ref<ResourceInstanceLifecycleState | undefined>();

const hasPersistedResourceInstance = computed(() => {
    return Boolean(props.resourceInstanceId);
});

const canEditResourceInstances = computed(() => {
    return (
        hasPersistedResourceInstance.value &&
        Boolean(currentLifecycleState.value?.can_edit_resource_instances)
    );
});

const canDeleteResourceInstances = computed(() => {
    return (
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
        ?.node_value.url;
});

onMounted(async () => {
    try {
        if (!props.resourceInstanceId) {
            label.value = {
                value: $gettext("New Scheme"),
                language_id: selectedLanguage.value.code,
                valuetype_id: PREF_LABEL,
            };
            return;
        }

        const resourceInstanceId = props.resourceInstanceId;

        const lingoResourcePromise = fetchLingoResource(
            props.graphSlug,
            resourceInstanceId,
        );

        const schemeResourcePromise = fetchSchemeResource(resourceInstanceId);

        const resourceIdentifiersPromise =
            fetchResourceIdentifiers(resourceInstanceId);

        const conceptIdentifierCounterPromise = fetchConceptIdentifierCounter(
            resourceInstanceId,
        ).catch(() => undefined);

        const schemeURITemplatePromise = fetchSchemeURITemplate(
            resourceInstanceId,
        ).catch(() => undefined);

        const lifecycleStatePromise =
            fetchResourceInstanceLifecycleState(resourceInstanceId);

        const [
            fetchedScheme,
            fetchedSchemeResource,
            fetchedResourceIdentifiers,
            fetchedConceptIdentifierCounter,
            fetchedSchemeURITemplate,
            fetchedLifecycleState,
        ] = await Promise.all([
            lingoResourcePromise,
            schemeResourcePromise,
            resourceIdentifiersPromise,
            conceptIdentifierCounterPromise,
            schemeURITemplatePromise,
            lifecycleStatePromise,
        ]);

        scheme.value = fetchedScheme;

        label.value = getItemLabel(
            fetchedSchemeResource,
            selectedLanguage.value.code,
            systemLanguage.code,
        );

        identifierValue.value = fetchedResourceIdentifiers?.[0]?.identifier;
        resourceIdentifierId.value = fetchedResourceIdentifiers?.[0]?.id;

        conceptIdentifierCounter.value = fetchedConceptIdentifierCounter;
        schemeURITemplate.value = fetchedSchemeURITemplate;

        currentLifecycleState.value =
            fetchedLifecycleState as ResourceInstanceLifecycleState;

        if (!schemeURITemplate.value?.url_template) {
            const publicServerAddressResponse =
                await fetchPublicServerAddress();
            publicServerAddress.value =
                publicServerAddressResponse?.PUBLIC_SERVER_ADDRESS;
        }

        extractSchemeHeaderData(fetchedScheme);
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
});

function openExportDialog() {
    exportDialogKey.value++;
    showExportDialog.value = true;
}

function extractSchemeHeaderData(scheme: ResourceInstanceResult) {
    const name = scheme?.name;
    const descriptor = extractDescriptors(scheme, systemLanguage);
    const principalUser = "Anonymous";

    data.value = {
        name: name,
        descriptor: descriptor,
        principalUser: principalUser,
        lifeCycleState: currentLifecycleState.value?.name || "--",
    };
}

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
</script>

<template>
    <ConfirmDialog group="delete-scheme" />
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

                    <div class="header-buttons">
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
                        ></Button>

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
                            :resource-instance-id="props.resourceInstanceId"
                            @change="onLifecycleStateChange"
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
                            $gettext("URI (provisonal): ")
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

                <div
                    class="header-row"
                    style="padding-bottom: 1rem"
                >
                    <ConceptIdentifierCounterField
                        :resource-instance-id="props.resourceInstanceId"
                        :can-edit-resource-instances="canEditResourceInstances"
                        :concept-identifier-counter="conceptIdentifierCounter"
                        @update="onConceptIdentifierCounterUpdate"
                    />
                </div>

                <div class="header-row metadata-container">
                    <div class="language-chip-container">
                        <span class="scheme-language">
                            {{ $gettext("English (en)") }}
                        </span>
                        <span class="scheme-language">
                            {{ $gettext("German (de)") }}
                        </span>
                        <span class="scheme-language">
                            {{ $gettext("French (fr)") }}
                        </span>
                        <span class="add-language">
                            {{ $gettext("Add Language") }}
                        </span>
                    </div>

                    <div class="lifecycle-container">
                        <div class="header-item">
                            <span class="header-item-label">
                                {{ $gettext("Life cycle state:") }}
                            </span>
                            <span class="header-item-value">
                                {{ data?.lifeCycleState }}
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
    gap: 0.25rem;
    margin-top: 0;
    padding-bottom: 1rem;
    justify-content: space-between;
    align-items: flex-start;
}

.language-chip-container {
    display: flex;
    gap: 0.25rem;
    align-items: center;
    flex-wrap: wrap;
    min-width: 0;
}

.add-language:hover {
    cursor: pointer;
}

.lifecycle-container {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    min-width: 0;
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
