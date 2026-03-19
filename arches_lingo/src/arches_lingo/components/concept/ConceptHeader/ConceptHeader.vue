<script setup lang="ts">
import { computed, inject, onMounted, ref, watch } from "vue";

import { useGettext } from "vue3-gettext";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import { storeToRefs } from "pinia";

import Button from "primevue/button";
import Skeleton from "primevue/skeleton";

import DeleteConceptDialog from "@/arches_lingo/components/concept/ConceptHeader/components/DeleteConceptDialog.vue";
import ExportThesauri from "@/arches_lingo/components/scheme/SchemeHeader/components/ExportThesauri.vue";
import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import {
    fetchLingoResource,
    fetchResourceIdentifiers,
    upsertLingoTile,
} from "@/arches_lingo/api.ts";
import {
    CONCEPT_ICON,
    CONCEPT_TYPE_NODE_ALIAS,
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    EDIT,
    ERROR,
    GUIDE_TERM_ICON,
    GUIDE_TERM_URI,
    NEW_CONCEPT,
    SUCCESS,
    TOP_CONCEPT_ICON,
    VIEW,
} from "@/arches_lingo/constants.ts";
import { PREF_LABEL } from "@/arches_controlled_lists/constants.ts";

import { routeNames } from "@/arches_lingo/routes.ts";

import {
    extractDescriptors,
    navigateToSchemeOrConcept,
} from "@/arches_lingo/utils.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";

import { useEditLog } from "@/arches_lingo/composables/useEditLog.ts";
import { useResourceStore } from "@/arches_lingo/composables/useResourceStore.ts";
import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

import type { Ref } from "vue";
import type {
    ConceptClassificationStatusAliases,
    ConceptHeaderData,
    DataComponentMode,
    DeleteConceptStrategy,
    Identifier,
    ResourceInstanceLifecycleState,
    ResourceInstanceResult,
} from "@/arches_lingo/types.ts";
import type { Label } from "@/arches_controlled_lists/types.ts";
import type { ReferenceSelectValue } from "@/arches_controlled_lists/datatypes/reference-select/types.ts";

const props = defineProps<{
    mode: DataComponentMode;
    sectionTitle: string;
    componentName: string;
    graphSlug: string;
    resourceInstanceId: string | undefined;
    nodegroupAlias: string;
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

const userStore = useUserStore();
const { isEditor } = userStore;
const resourceStore = useResourceStore();
const conceptStore = useConceptStore();

const { openEditLog } = useEditLog(() => props.graphSlug);
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

const concept = ref<ResourceInstanceResult>();
const isTopConcept = ref(false);
const data = ref<ConceptHeaderData>();
const isLoading = ref(true);
const showExportDialog = ref(false);
const exportDialogKey = ref(0);
const showDeleteDialog = ref(false);
const conceptIdentifierValue = ref<string>();
const conceptTypeTile = ref();

onMounted(async () => {
    try {
        const resourceInstanceId = props.resourceInstanceId;
        if (!resourceInstanceId) return;

        const [fetchedConcept, resourceIdentifiers] = await Promise.all([
            fetchLingoResource(props.graphSlug, resourceInstanceId),
            fetchResourceIdentifiers(resourceInstanceId),
        ]);

        concept.value = fetchedConcept;
        conceptTypeTile.value =
            concept.value?.aliased_data?.[CONCEPT_TYPE_NODE_ALIAS];
        conceptIdentifierValue.value = resourceIdentifiers?.[0]?.identifier;

        extractConceptHeaderData(fetchedConcept);
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch concept"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
    }
});

watch(
    [() => resourceStore.resource.value, () => resourceStore.error.value],
    async ([resource, storeError]) => {
        if (storeError) {
            toast.add({
                severity: ERROR,
                life: DEFAULT_ERROR_TOAST_LIFE,
                summary: $gettext("Unable to fetch concept"),
                detail: storeError.message,
            });
            isLoading.value = false;
            return;
        }
        if (!resource || !props.resourceInstanceId) return;

        concept.value = resource;
        conceptTypeTile.value =
            resource.aliased_data?.[CONCEPT_TYPE_NODE_ALIAS];
        isTopConcept.value =
            (resource.aliased_data?.top_concept_of ?? []).length > 0;
        extractConceptHeaderData(resource);
        isLoading.value = false;
    },
    { immediate: true },
);

watch(
    () => selectedLanguage.value.code,
    () => {
        if (concept.value) {
            extractConceptHeaderData(concept.value);
        }
    },
);

const label = computed<Label | undefined>(() => {
    if (!props.resourceInstanceId) {
        return {
            value: $gettext("New Concept"),
            language_id: selectedLanguage.value.code,
            valuetype_id: PREF_LABEL,
        };
    }

    const storedConcept = conceptStore.findConcept(props.resourceInstanceId);
    if (!storedConcept) return undefined;

    return getItemLabel(
        { labels: [...storedConcept.labels] },
        selectedLanguage.value.code,
        systemLanguage.value.code,
    );
});

const parentConceptLabelMap = computed<Map<string, Label[]>>(() => {
    const map = new Map<string, Label[]>();
    for (const parent of data.value?.parentConcepts ?? []) {
        const id = parent.details[0]?.resource_id;

        if (id) {
            map.set(id, conceptStore.findConcept(id)?.labels ?? []);
        }
    }
    return map;
});

const conceptIcon = computed(() => {
    const typeNodeValue =
        conceptTypeTile.value?.aliased_data?.[CONCEPT_TYPE_NODE_ALIAS]
            ?.node_value;
    if (isGuideTermType(typeNodeValue)) return GUIDE_TERM_ICON;
    if (isTopConcept.value) return TOP_CONCEPT_ICON;
    return CONCEPT_ICON;
});

const lifecycleStateLabel = computed(() => {
    return resourceInstanceLifecycleState?.value?.name ?? "--";
});

const canEditResourceInstances = computed(() => {
    return (
        isEditor &&
        props.resourceInstanceId &&
        resourceInstanceLifecycleState?.value?.can_edit_resource_instances
    );
});

const canDeleteResourceInstances = computed(() => {
    return (
        isEditor &&
        props.resourceInstanceId &&
        resourceInstanceLifecycleState?.value?.can_delete_resource_instances
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
            tileid: conceptTypeTile.value?.tileid,
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
    if (!concept.value?.resourceinstanceid) return;
    showDeleteDialog.value = true;
}

async function onDeleteConfirmed(strategy: DeleteConceptStrategy | null) {
    showDeleteDialog.value = false;
    if (!concept.value) return;

    const schemeIdentifier =
        concept.value.aliased_data?.part_of_scheme?.aliased_data.part_of_scheme
            ?.node_value;

    try {
        if (strategy === null) {
            console.log("[stub] deleteLingoResource", {
                graphSlug: props.graphSlug,
                conceptId: concept.value.resourceinstanceid,
            });
        } else {
            console.log("[stub] deleteConceptWithStrategy", {
                graphSlug: props.graphSlug,
                conceptId: concept.value.resourceinstanceid,
                strategy,
            });
        }

        router.push({
            name: routeNames.scheme,
            params: { id: schemeIdentifier },
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

function openExportDialog() {
    exportDialogKey.value++;
    showExportDialog.value = true;
}

function addChild() {
    const schemeId = data.value?.partOfScheme?.node_value?.[0]?.resourceId;
    const parentId = props.resourceInstanceId;

    if (!schemeId || !parentId) return;

    navigateToSchemeOrConcept(router, NEW_CONCEPT, {
        scheme: schemeId,
        parent: parentId,
    });
}

function extractConceptHeaderData(resource: ResourceInstanceResult) {
    const aliased_data = resource?.aliased_data;

    const name = resource?.name;
    const descriptor = extractDescriptors(resource, selectedLanguage.value);
    const principalUser = resource?.principal_user_display_name ?? undefined;

    const uri = aliased_data?.uri?.aliased_data?.uri_content?.node_value;
    const partOfScheme =
        aliased_data?.part_of_scheme?.aliased_data?.part_of_scheme;
    const schemeId = partOfScheme?.node_value?.[0]?.resourceId;
    const matchingScheme = conceptStore.schemes.find(
        (candidateScheme) => candidateScheme.id === schemeId,
    );
    let schemeLabel: string | undefined;
    if (matchingScheme) {
        schemeLabel = getItemLabel(
            { labels: [...matchingScheme.labels] },
            selectedLanguage.value.code,
            systemLanguage.value.code,
        ).value;
    }

    const parentConcepts = (aliased_data?.classification_status || []).flatMap(
        (tile: ConceptClassificationStatusAliases) =>
            tile?.aliased_data?.classification_status_ascribed_classification ||
            [],
    );
    const identifier = (aliased_data?.identifier || [])
        .map(
            (tile: Identifier) =>
                tile?.aliased_data?.identifier_content?.node_value,
        )
        .join(", ");

    data.value = {
        name,
        descriptor,
        uri,
        principalUser,
        lifeCycleState: lifecycleStateLabel.value,
        partOfScheme,
        schemeLabel,
        parentConcepts,
        identifier,
    };
}
</script>

<template>
    <DeleteConceptDialog
        v-if="concept && showDeleteDialog"
        :concept-id="concept.resourceinstanceid"
        :concept-name="label?.value"
        @confirm="onDeleteConfirmed"
        @cancel="showDeleteDialog = false"
    />
    <ExportThesauri
        v-if="concept && showExportDialog"
        :key="exportDialogKey"
        :resource-id="concept.resourceinstanceid"
        :resource-name="label?.value"
    />
    <Skeleton
        v-if="isLoading || !userStore.user"
        class="loading-skeleton"
    />
    <div
        v-else
        class="concept-header"
    >
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
                        :graph-slug="props.graphSlug"
                        :mode="isEditor ? EDIT : VIEW"
                        :aliased-node-data="
                            conceptTypeTile?.aliased_data?.[
                                CONCEPT_TYPE_NODE_ALIAS
                            ]
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
                    v-if="canDeleteResourceInstances"
                    icon="pi pi-trash"
                    :severity="DANGER"
                    class="delete-button"
                    :label="$gettext('Delete')"
                    :aria-label="$gettext('Delete Concept')"
                    @click="confirmDelete"
                />
            </div>
        </div>

        <div class="header-content">
            <div class="concept-header-section">
                <div class="header-row">
                    <div class="header-item">
                        <span class="header-item-label">
                            {{ $gettext("Identifier:") }}
                        </span>
                        <span class="header-item-value">
                            {{ conceptIdentifierValue || $gettext("None") }}
                        </span>
                    </div>
                    <div>
                        <span class="header-item-label">{{
                            $gettext("URI: ")
                        }}</span>
                        <Button
                            v-if="data?.uri"
                            :label="data?.uri"
                            class="concept-uri"
                            variant="link"
                            as="a"
                            :href="data?.uri"
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
                    <div class="header-item">
                        <span class="header-item-label">
                            {{ $gettext("Scheme:") }}
                        </span>
                        <span class="header-item-value">
                            <RouterLink
                                v-if="data?.partOfScheme?.node_value"
                                :to="`/scheme/${data?.partOfScheme?.node_value?.[0]?.resourceId}`"
                            >
                                {{
                                    data?.schemeLabel ||
                                    data?.partOfScheme?.display_value
                                }}
                            </RouterLink>
                            <span v-else>--</span>
                        </span>
                    </div>

                    <div class="header-item">
                        <span class="header-item-label">
                            {{ $gettext("Life cycle state:") }}
                        </span>
                        <span class="header-item-value">
                            {{ lifecycleStateLabel }}
                        </span>
                    </div>
                </div>
            </div>
            <div
                class="header-row"
                :class="{ 'top-concept-owner': isTopConcept }"
            >
                <div
                    v-if="!isTopConcept"
                    class="header-item"
                >
                    <span class="header-item-label">
                        {{ $gettext("Parent Concept(s):") }}
                    </span>
                    <span
                        v-for="parent in data?.parentConcepts"
                        :key="parent.details[0].resource_id"
                        class="header-item-value parent-concept"
                    >
                        <RouterLink
                            :to="`/concept/${parent.details[0].resource_id}`"
                        >
                            {{
                                getItemLabel(
                                    {
                                        labels:
                                            parentConceptLabelMap.get(
                                                parent.details[0].resource_id,
                                            ) ?? [],
                                    },
                                    selectedLanguage.code,
                                    systemLanguage.code,
                                ).value || parent.details[0].display_value
                            }}
                        </RouterLink>
                    </span>
                </div>
                <div class="header-item">
                    <span class="header-item-label">
                        {{ $gettext("Owner:") }}
                    </span>
                    <span class="header-item-value">
                        {{ data?.principalUser || $gettext("Anonymous") }}
                    </span>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.concept-header {
    padding-top: 0rem;
    padding-bottom: 1rem;
    background: var(--p-header-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    min-height: 8.5rem;
    box-sizing: border-box;
}

.header-content {
    padding-top: 0.75rem;
    padding-inline-start: 1rem;
    padding-inline-end: 1rem;
    box-sizing: border-box;
}

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

.loading-skeleton {
    width: 100%;
    height: 9rem;
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

.concept-uri {
    font-size: var(--p-lingo-font-size-small);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-primary-500);
}

.p-button-link {
    padding: 0;
    margin: 0;
}

.header-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    flex-wrap: wrap;
    column-gap: 1rem;
    row-gap: 0.25rem;
    min-width: 0;
}

.header-item {
    display: inline-flex;
    align-items: baseline;
    min-width: 0;
}

.header-item-label {
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
    margin-inline-end: 0.25rem;
}

.header-item-value {
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
    margin-inline-end: 0.25rem;
    min-width: 0;
}

.header-item-value,
:deep(a) {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-primary-500);
}

.top-concept-owner {
    justify-self: end;
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

.parent-concept {
    margin-inline-end: 0.5rem;
}

.parent-concept:hover a {
    color: var(--p-primary-700);
}

:deep(.concept-type-widget .p-icon.p-treeselect-clear-icon) {
    display: none;
}
</style>
