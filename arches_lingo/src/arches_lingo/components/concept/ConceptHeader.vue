<script setup lang="ts">
import { inject, onMounted, ref } from "vue";

import { useConfirm } from "primevue/useconfirm";
import { useGettext } from "vue3-gettext";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";

import ConfirmDialog from "primevue/confirmdialog";
import Button from "primevue/button";
import SelectButton from "primevue/selectbutton";
import RadioButton from "primevue/radiobutton";
import Select from "primevue/select";

//Placeholder for export button panel
import Popover from "primevue/popover";

import Skeleton from "primevue/skeleton";

import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";

import { fetchLingoResource, deleteLingoResource } from "@/arches_lingo/api.ts";
import { extractDescriptors } from "@/arches_lingo/utils.ts";
import { DANGER, SECONDARY } from "@/arches_lingo/constants.ts";

import type {
    ConceptHeaderData,
    ConceptClassificationStatusAliases,
    ResourceInstanceResult,
    DataComponentMode,
} from "@/arches_lingo/types.ts";

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

const concept = ref<ResourceInstanceResult>();
const data = ref<ConceptHeaderData>();
const isLoading = ref(true);

onMounted(async () => {
    try {
        if (!props.resourceInstanceId) {
            return;
        }

        concept.value = await fetchLingoResource(
            props.graphSlug,
            props.resourceInstanceId,
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

//Placeholder for export button panel
const exportDialog = ref();
const toggle = (event: Event) => {
    exportDialog.value.toggle(event);
};

//Placeholder for export type
const exporter = ref("Concept Only");
const exporterOptions = ref(["Concept Only", "Concept + Children"]);

//Placeholder for export format radio button group
const exportFormat = ref();
const exportformatOptions = ref([
    { label: "csv", value: "csv" },
    { label: "SKOS", value: "skos" },
    { label: "rdf", value: "rdf" },
    { label: "JSON-LD", value: "jsonld" },
]);

//Placeholder for concept Type
const conceptType = ref();
const ctype = ref([
    { name: "Concept", code: "c" },
    { name: "Guide Term", code: "gt" },
]);

function extractConceptHeaderData(concept: ResourceInstanceResult) {
    const aliased_data = concept?.aliased_data;

    const name = concept?.name;
    const descriptor = extractDescriptors(concept, systemLanguage);
    // TODO: get human-readable user name from resource endpoint
    const principalUser = "Anonymous"; //concept?.principalUser; // returns userid int
    // TODO: get human-readable life cycle state from resource endpoint
    const lifeCycleState = $gettext("Draft");
    const uri = aliased_data?.uri?.aliased_data?.uri_content?.url;
    const partOfScheme =
        aliased_data?.part_of_scheme?.aliased_data?.part_of_scheme;
    const parentConcepts = (aliased_data?.classification_status || []).flatMap(
        (tile: ConceptClassificationStatusAliases) =>
            tile?.aliased_data?.classification_status_ascribed_classification ||
            [],
    );

    data.value = {
        name: name,
        descriptor: descriptor,
        uri: uri,
        principalUser: principalUser,
        lifeCycleState: lifeCycleState,
        partOfScheme: partOfScheme,
        parentConcepts: parentConcepts,
    };
}
</script>

<template>
    <ConfirmDialog group="delete-concept" />
    <Skeleton
        v-if="isLoading"
        style="width: 100%"
    />
    <div
        v-else
        class="concept-header"
    >
        <div class="concept-header-toolbar">
            <div class="concept-details">
                <h2 v-if="data?.descriptor?.name">
                    <div class="concept-name">
                        <!-- To do: change icon based on concept type -->
                        <i class="pi pi-tag"></i>
                        <span>
                            {{ data?.descriptor?.name }}

                            <span
                                v-if="data?.descriptor?.language"
                                class="concept-label-lang"
                            >
                                ({{ data?.descriptor?.language }})
                            </span>
                        </span>
                    </div>
                </h2>
                <div class="card flex justify-center">
                    <Select
                        v-model="conceptType"
                        :options="ctype"
                        option-label="name"
                        placeholder="Concept"
                        checkmark
                        :highlight-on-select="false"
                    />
                </div>
            </div>
            <div class="header-buttons">
                <!-- Placeholder export button -->
                <Button
                    :aria-label="$gettext('Export')"
                    class="add-button"
                    @click="toggle"
                >
                    <span><i class="pi pi-cloud-download"></i></span>
                    <span>Export</span>
                </Button>
                <Popover
                    ref="exportDialog"
                    class="export-panel"
                >
                    <div class="exports-panel-container">
                        <div class="container-title">
                            <h3>
                                {{ $gettext("Concept Export") }}
                            </h3>
                        </div>
                        <div class="options-container">
                            <h4>
                                {{ $gettext("Export Options") }}
                            </h4>
                            <!-- TODO: export options go here -->
                            <SelectButton
                                v-model="exporter"
                                :options="exporterOptions"
                            />
                        </div>
                        <div class="formats-container">
                            <h4>
                                {{ $gettext("Export Format") }}
                            </h4>
                            <div>
                                <span
                                    v-for="option in exportformatOptions"
                                    :key="option.value"
                                    class="selection"
                                >
                                    <RadioButton
                                        :key="option.value"
                                        v-model="exportFormat"
                                        :input-id="option.value"
                                        :value="option.value"
                                        :label="option.label"
                                    ></RadioButton>
                                    <label :for="option.value">{{
                                        option.label
                                    }}</label>
                                </span>
                            </div>
                        </div>
                        <div class="export-footer">
                            <Button
                                icon="pi pi-file-export"
                                :label="$gettext('Export')"
                                class="add-button"
                            ></Button>
                            <Button
                                icon="pi pi-trash"
                                :label="$gettext('Cancel')"
                                class="add-button"
                            ></Button>
                        </div>
                    </div>
                </Popover>

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
                        <span class="header-item-value"> 0032775 </span>
                    </div>
                    <div>
                        <span class="header-item-label">{{
                            $gettext("URI (provisonal): ")
                        }}</span>
                        <Button
                            :label="
                                data?.uri ||
                                'https://fgi.lingo.com/concepts/0032775'
                            "
                            class="concept-uri"
                            variant="link"
                            as="a"
                            :href="data?.uri"
                            target="_blank"
                            rel="noopener"
                            :disabled="!data?.uri"
                        ></Button>
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
}

.header-content {
    padding-top: 0.75rem;
    padding-inline-start: 1rem;
    padding-inline-end: 1.5rem;
}

.concept-header-toolbar {
    height: 3rem;
    background: var(--p-header-toolbar-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-inline-start: 1rem;
    padding-inline-end: 1rem;
}

.concept-details {
    display: flex;
    align-items: anchor-center;
    gap: 0.5rem;
}

.concept-name {
    display: flex;
    align-items: anchor-center;
    gap: 0.25rem;
}

.p-select {
    margin: 0rem 0.5rem;
    border-radius: 0.125rem;
    box-shadow: none;
    width: 10rem;
}

h2 {
    margin-top: 0;
    margin-bottom: 0;
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
}

.delete-button {
    font-size: var(--p-lingo-font-size-small);
}

.header-buttons {
    display: flex;
    gap: 0.25rem;
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
}

.header-item {
    display: inline-flex;
    align-items: baseline;
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
</style>
