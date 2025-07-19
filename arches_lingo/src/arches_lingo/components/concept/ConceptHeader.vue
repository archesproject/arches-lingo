<script setup lang="ts">
import { inject, onMounted, ref } from "vue";

import { useConfirm } from "primevue/useconfirm";
import { useGettext } from "vue3-gettext";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";

import ConfirmDialog from "primevue/confirmdialog";
import Button from "primevue/button";
import SelectButton from 'primevue/selectbutton';
import RadioButton from 'primevue/radiobutton';


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
                            ?.aliased_data.part_of_scheme?.interchange_value;

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
const exportdialog = ref();
const toggle = (event) => {
    exportdialog.value.toggle(event);
}

//Placeholder for export type
const exporter = ref('Concept Only');
const exporteroptions = ref(['Concept Only', 'Concept + Children']);

//Placeholder for export format radio button group
const exportformat = ref('');


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

    function openExportMenu(event: MouseEvent) {
    popover.value!.toggle(event);
}
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
            <h2 v-if="data?.descriptor?.name">
                
                <span>
                    {{ data?.descriptor?.name }}

                    <span
                        v-if="data?.descriptor?.language"
                        class="concept-label-lang"
                    >
                        ({{ data?.descriptor?.language }})
                    </span>
                </span>
            </h2>
            <div class="header-buttons">

                <!-- Placeholder export button -->
                <Button
                    :aria-label="$gettext('Export')"
                    @click="toggle"
                    class="add-button"
                >
                    <span><i class="pi pi-cloud-download"></i></span>
                    <span>Export</span>
                </Button>
                <Popover
                    ref="exportdialog"
                    class="export-panel"
                >
                    <div class="exports-panel-container">
                        <div class="container-title">
                            <h3>
                                Concept Export
                            </h3>
                        </div>
                        <div class="options-container">
                            <h4>
                                Export Options
                            </h4>
                            <!-- TODO: export options go here -->
                            <SelectButton v-model="exporter" :options="exporteroptions" />
                        </div>
                        <div class="formats-container">
                            <h4>
                                Export Formats
                            </h4>
                            <!-- TODO: export format selection goes here -->
                            <div>
                                <div class="export-selection">
                                    <RadioButton v-model="exportformat" inputId="format1" name="pizza" value="csv" />
                                    <label for="ingredient1">csv</label>
                                </div>
                                <div class="export-selection">
                                    <RadioButton v-model="exportformat" inputId="format2" name="pizza" value="SKOS" />
                                    <label for="ingredient2">SKOS</label>
                                </div>
                                <div class="export-selection">
                                    <RadioButton v-model="exportformat" inputId="format3" name="pizza" value="rdf" />
                                    <label for="ingredient3">rdf</label>
                                </div>
                                <div class="export-selection">
                                    <RadioButton v-model="exportformat" inputId="format4" name="pizza" value="JSON-LD" />
                                    <label for="ingredient4">JSON-LD</label>
                                </div>
                            </div>
                        </div>
                        <div class="export-footer">
                            <Button
                                icon="pi pi-trash"
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
                        <span class="header-item-value">
                            0032775
                        </span>
                    </div>
                    <div>
                        <span class="header-item-label">{{ $gettext("URI (provisonal): ") }}</span>
                        <Button
                            :label="data?.uri || 'https://fgi.lingo.com/concepts/0032775'"
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
                                v-if="data?.partOfScheme?.interchange_value"
                                :to="`/scheme/${data?.partOfScheme?.interchange_value}`"
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
                            {{ data?.lifeCycleState ? data?.lifeCycleState : "--" }}
                        </span>
                    </div>
                </div>
                <div class="header-row">
                    <div class="header-item">
                        <span class="header-item-label">
                            {{ $gettext("Parent Concept(s):") }}
                        </span>
                        <span
                            v-for="parent in data?.parentConcepts"
                            :key="parent.interchange_value"
                            class="header-item-value parent-concept"
                        >
                            <RouterLink
                                :to="`/concept/${parent.interchange_value}`"
                                >{{ parent.display_value }}</RouterLink
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
    </div>
</template>

<style scoped>
.concept-header {
    padding-top: 0 rem;
    padding-bottom: 1rem;
    background: var(--p-header-background);
    border-bottom: 0.06rem solid var(--p-header-border);
}

.header-content {
    padding-top: .75rem;
    padding-inline-start: 1rem;
    padding-inline-end: 1.5rem;
}

.concept-header-toolbar {
    height: 3rem;
    background: var(--p-header-toolbar-background);
    border-bottom: 1px solid var(--p-header-toolbar-border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-inline-start: 1rem;
    padding-inline-end: 1rem;
}

h2 {
    margin-top: 0;
    margin-bottom: 0;
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
}

.add-button {
    background: var(--p-header-button-background);
    color: var(--p-header-button-color);
    border-color: var(--p-header-button-border);
    font-size: var(--p-lingo-font-size-small);
}

.delete-button {
    font-size: var(--p-lingo-font-size-small);
}

.header-buttons {
    display: flex;
    gap: .25rem;
}

.export-panel {
    padding: 1rem;
}

.exports-panel-container {
    font-family: 'Lucida Sans', 'Lucida Sans Regular', 'Lucida Grande', 'Lucida Sans Unicode', Geneva, Verdana, sans-serif;
    font-weight: 300;
    padding: 0 1rem;
}

.options-container {
    padding: 0 0 .75rem 0;
}

.options-container h4 {
    margin: 0;
    padding-bottom: .4rem;
}

.formats-container {
    padding: 0 0 .75rem 0;
}

.formats-container h4 {
    margin: 0;
}

.export-selection {
    display: flex;
    gap: .5rem;
    padding: .2rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    align-items: center;
    color: var(--p-list-option-icon-color);
}

.export-footer {
    display: flex;
    flex-direction: row-reverse;
    gap: .25rem;
    border-top: 0.06rem solid var(--p-header-border);
    padding: .5rem 0 0 0;
}

.container-title {
    font-size: var(--p-lingo-font-size-normal);
    border-bottom: 0.0625rem solid var(--p-header-border);
    margin-bottom: 0.5rem;
}

.container-title h3 {
    padding-top: .5rem;
    margin: 0rem 0rem .25rem 0rem;
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
    border-radius: .125rem;
}

:deep(.p-togglebutton-checked .p-togglebutton-content) {
    border-radius: .125rem;
}

:deep(.p-selectbutton .p-togglebutton:first-child){
    border-radius: .125rem;
}

.parent-concept {
    margin-inline-end: 0.5rem;
}
</style>
