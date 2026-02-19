<script setup lang="ts">
import { inject, onMounted, ref, type Ref } from "vue";

import { useConfirm } from "primevue/useconfirm";
import { useGettext } from "vue3-gettext";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";

import ConfirmDialog from "primevue/confirmdialog";
import Button from "primevue/button";
import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";
import { upsertLingoTile } from "@/arches_lingo/api.ts";
import Skeleton from "primevue/skeleton";

import ExportThesauri from "@/arches_lingo/components/scheme/SchemeHeader/components/ExportThesauri.vue";

import {
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    EDIT,
    ERROR,
    SECONDARY,
    SUCCESS,
    systemLanguageKey,
    selectedLanguageKey,
    CONCEPT_TYPE_NODE_ALIAS,
} from "@/arches_lingo/constants.ts";
import { PREF_LABEL } from "@/arches_controlled_lists/constants.ts";

import {
    fetchLingoResource,
    deleteLingoResource,
    fetchConceptResource,
} from "@/arches_lingo/api.ts";
import { extractDescriptors } from "@/arches_lingo/utils.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";

import type {
    ConceptHeaderData,
    ConceptClassificationStatusAliases,
    ConceptIdentifier,
    ResourceInstanceResult,
    DataComponentMode,
} from "@/arches_lingo/types.ts";
import type { Label } from "@/arches_controlled_lists/types";
import type { ReferenceSelectValue } from "@/arches_controlled_lists/datatypes/reference-select/types.ts";

import type { Language } from "@/arches_component_lab/types.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

const props = defineProps<{
    mode: DataComponentMode;
    sectionTitle: string;
    componentName: string;
    graphSlug: string;
    resourceInstanceId: string | undefined;
    nodegroupAlias: string;
}>();

const refreshSchemeHierarchy = inject<() => void>("refreshSchemeHierarchy");

const toast = useToast();
const { $gettext } = useGettext();
const confirm = useConfirm();
const router = useRouter();

const systemLanguage = inject(systemLanguageKey) as Language;
const selectedLanguage = inject(selectedLanguageKey) as Ref<Language>;

const concept = ref<ResourceInstanceResult>();
const label = ref<Label>();
const data = ref<ConceptHeaderData>();
const isLoading = ref(true);
const showExportDialog = ref(false);
const exportDialogKey = ref(0);

const conceptTypeTile = ref();

async function onConceptTypeChange(newValue: ReferenceSelectValue) {
    try {
        conceptTypeTile.value = await upsertLingoTile(
            props.graphSlug,
            CONCEPT_TYPE_NODE_ALIAS,
            {
                resourceinstance: props.resourceInstanceId,
                aliased_data: {
                    [CONCEPT_TYPE_NODE_ALIAS]: newValue,
                },
                tileid: conceptTypeTile.value?.tileid,
            },
        );
        toast.add({
            severity: SUCCESS,
            summary: $gettext("Concept type updated"),
            life: DEFAULT_TOAST_LIFE,
        });
    } catch (error) {
        toast.add({
            severity: ERROR,
            summary: $gettext("Failed to update concept type"),
            detail: error instanceof Error ? error.message : undefined,
            life: DEFAULT_ERROR_TOAST_LIFE,
        });
    }
}

onMounted(async () => {
    try {
        if (!props.resourceInstanceId) {
            label.value = {
                value: $gettext("New Concept"),
                language_id: selectedLanguage.value.code,
                valuetype_id: PREF_LABEL,
            };
            return;
        }

        concept.value = await fetchLingoResource(
            props.graphSlug,
            props.resourceInstanceId,
        );

        conceptTypeTile.value =
            concept.value?.aliased_data?.[CONCEPT_TYPE_NODE_ALIAS];

        const conceptResource = await fetchConceptResource(
            props.resourceInstanceId,
        );

        label.value = getItemLabel(
            conceptResource,
            selectedLanguage.value.code,
            systemLanguage.code,
        );

        extractConceptHeaderData(concept.value!);
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

function confirmDelete() {
    confirm.require({
        header: $gettext("Confirmation"),
        message: $gettext("Are you sure you want to delete this concept?"),
        group: "delete-concept",
        accept: () => {
            if (!concept.value) {
                return;
            }

            try {
                deleteLingoResource(
                    props.graphSlug,
                    concept.value.resourceinstanceid,
                ).then(() => {
                    const schemeIdentifier =
                        concept.value!.aliased_data?.part_of_scheme
                            ?.aliased_data.part_of_scheme?.node_value;

                    router.push({
                        name: routeNames.scheme,
                        params: { id: schemeIdentifier },
                    });

                    refreshSchemeHierarchy!();
                });
            } catch (error) {
                toast.add({
                    severity: ERROR,
                    life: DEFAULT_ERROR_TOAST_LIFE,
                    summary: $gettext("Error deleting concept"),
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

function openExportDialog() {
    exportDialogKey.value++;
    showExportDialog.value = true;
}

function extractConceptHeaderData(concept: ResourceInstanceResult) {
    const aliased_data = concept?.aliased_data;

    const name = concept?.name;
    const descriptor = extractDescriptors(concept, systemLanguage);
    // TODO: get human-readable user name from resource endpoint
    const principalUser = "Anonymous"; //concept?.principalUser; // returns userid int
    // TODO: get human-readable life cycle state from resource endpoint
    const lifeCycleState = $gettext("Draft");
    const uri = aliased_data?.uri?.aliased_data?.uri_content?.node_value;
    const partOfScheme =
        aliased_data?.part_of_scheme?.aliased_data?.part_of_scheme;
    const parentConcepts = (aliased_data?.classification_status || []).flatMap(
        (tile: ConceptClassificationStatusAliases) =>
            tile?.aliased_data?.classification_status_ascribed_classification ||
            [],
    );
    const identifier = (aliased_data?.identifier || [])
        .map(
            (tile: ConceptIdentifier) =>
                tile?.aliased_data?.identifier_content?.node_value,
        )
        .join(", ");

    data.value = {
        name: name,
        descriptor: descriptor,
        uri: uri,
        principalUser: principalUser,
        lifeCycleState: lifeCycleState,
        partOfScheme: partOfScheme,
        parentConcepts: parentConcepts,
        identifier: identifier,
    };
}
</script>

<template>
    <ConfirmDialog group="delete-concept" />
    <ExportThesauri
        v-if="concept && showExportDialog"
        :key="exportDialogKey"
        :resource-id="concept.resourceinstanceid"
        :resource-name="label?.value"
    />
    <Skeleton
        v-if="isLoading"
        style="width: 100%; height: 9rem"
    />
    <div
        v-else
        class="concept-header"
    >
        <div class="concept-header-toolbar">
            <div class="concept-details">
                <h2>
                    <div class="concept-name">
                        <!-- To do: change icon based on concept type -->
                        <i class="pi pi-tag"></i>
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
                </h2>
                <div class="card flex justify-center">
                    <GenericWidget
                        v-if="concept && concept.resourceinstanceid"
                        :node-alias="CONCEPT_TYPE_NODE_ALIAS"
                        :graph-slug="props.graphSlug"
                        :mode="EDIT"
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
                    icon="pi pi-plus-circle"
                    :label="$gettext('Add Child')"
                    class="add-button"
                ></Button>

                <!-- TODO: button should reflect published state of concept: delete if draft, deprecate if URI is present -->
                <Button
                    icon="pi pi-trash"
                    severity="danger"
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
                    <!-- TODO: Life Cycle mgmt functionality goes here -->
                    <div class="header-item">
                        <span class="header-item-label">
                            {{ $gettext("Identifier:") }}
                        </span>
                        <span class="header-item-value">{{
                            data?.identifier || "--"
                        }}</span>
                    </div>
                    <div>
                        <span class="header-item-label">{{
                            $gettext("URI (provisonal): ")
                        }}</span>
                        <Button
                            v-if="data?.uri"
                            :label="data?.uri?.url_label || data?.uri?.url"
                            class="concept-uri"
                            variant="link"
                            as="a"
                            :href="data?.uri?.url"
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
                    <!-- TODO: Human-reable conceptid to be displayed here -->
                    <div class="header-item">
                        <span class="header-item-label">
                            {{ $gettext("Scheme:") }}
                        </span>
                        <span class="header-item-value">
                            <RouterLink
                                v-if="data?.partOfScheme?.node_value"
                                :to="`/scheme/${data?.partOfScheme?.node_value?.[0]?.resourceId}`"
                            >
                                {{ data?.partOfScheme?.display_value }}
                            </RouterLink>
                            <span v-else>--</span>
                        </span>
                    </div>

                    <!-- TODO: Life Cycle mgmt functionality goes here -->
                    <div class="header-item">
                        <span class="header-item-label">
                            {{ $gettext("Life cycle state:") }}
                        </span>
                        <span class="header-item-value">
                            {{
                                data?.lifeCycleState
                                    ? data?.lifeCycleState
                                    : "--"
                            }}
                        </span>
                    </div>
                </div>
            </div>
            <div class="header-row">
                <div class="header-item">
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
                            >{{ parent.details[0].display_value }}</RouterLink
                        >
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

h2 {
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
