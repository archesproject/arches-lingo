<script setup lang="ts">
import { inject, onMounted, ref } from "vue";
import { useGettext } from "vue3-gettext";

import { useConfirm } from "primevue/useconfirm";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import Skeleton from "primevue/skeleton";

import ConfirmDialog from "primevue/confirmdialog";
import Button from "primevue/button";
import SelectButton from "primevue/selectbutton";
import RadioButton from "primevue/radiobutton";
import Popover from "primevue/popover";

import {
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    SECONDARY,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";

import { deleteLingoResource, fetchLingoResource } from "@/arches_lingo/api.ts";
import { extractDescriptors } from "@/arches_lingo/utils.ts";

import type {
    DataComponentMode,
    ResourceInstanceResult,
    SchemeHeader,
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

const confirm = useConfirm();
const router = useRouter();
const toast = useToast();
const { $gettext } = useGettext();
const systemLanguage = inject(systemLanguageKey) as Language;

const scheme = ref<ResourceInstanceResult>();
const data = ref<SchemeHeader>();
const isLoading = ref(true);

function extractSchemeHeaderData(scheme: ResourceInstanceResult) {
    const name = scheme?.name;
    const descriptor = extractDescriptors(scheme, systemLanguage);
    // TODO: get human-readable user name from resource endpoint
    const principalUser = "Anonymous"; //scheme?.principalUser; // returns userid int
    // TODO: get human-readable life cycle state from resource endpoint
    const lifeCycleState = $gettext("Draft");

    data.value = {
        name: name,
        descriptor: descriptor,
        principalUser: principalUser,
        lifeCycleState: lifeCycleState,
    };
}

onMounted(async () => {
    try {
        if (!props.resourceInstanceId) {
            return;
        }

        scheme.value = await fetchLingoResource(
            props.graphSlug,
            props.resourceInstanceId,
        );

        extractSchemeHeaderData(scheme.value!);
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
</script>

<template>
    <ConfirmDialog group="delete-scheme" />

    <Skeleton
        v-if="isLoading"
        style="width: 100%"
    />

    <div
        v-else
        class="scheme-header"
    >
        <div class="scheme-header-panel">
            <div class="scheme-header-toolbar">
                <div class="header-row">
                    <div>
                        <h2 v-if="data?.descriptor?.name">
                            <span>
                                {{ data?.descriptor?.name }}

                                <span
                                    v-if="data?.descriptor?.language"
                                    class="scheme-label-lang"
                                >
                                    ({{ data?.descriptor?.language }})
                                </span>
                            </span>
                        </h2>
                    </div>

                    <div class="header-buttons">
                        <!-- Placeholder export button -->
                        <Button
                            :aria-label="$gettext('Export')"
                            class="add-button"
                            @click="toggle"
                        >
                            <span><i class="pi pi-cloud-download"></i></span>
                            <span>{{ $gettext("Export") }}</span>
                        </Button>
                        <Popover
                            ref="exportDialog"
                            class="export-panel"
                        >
                            <div class="exports-panel-container">
                                <div class="container-title">
                                    <h3>
                                        {{ $gettext("Scheme Export") }}
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
                            :label="$gettext('Add Top Concept')"
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

                        <!-- TODO: button should allow user to publish scheme if draft, retire scheme if published -->
                        <Button
                            icon="pi pi-book"
                            :label="$gettext('Publish')"
                            class="add-button"
                        ></Button>
                    </div>
                </div>
            </div>

            <div class="header-content">
                <!-- TODO: show Scheme URI here -->
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
                                'https://fgi.lingo.com/schemes/0032775'
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

                <div class="header-row metadata-container">
                    <!-- TODO: Load Scheme languages here -->
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
}

.scheme-header-toolbar {
    height: 3rem;
    background: var(--p-header-toolbar-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
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

.scheme-label-lang {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
    vertical-align: baseline;
}

.header-content {
    padding-top: 0.5rem;
    padding-inline-start: 1rem;
    padding-inline-end: 1.5rem;
}

.header-buttons {
    display: flex;
    gap: 0.25rem;
}

.p-button-link {
    padding: 0;
    margin: 0;
}

.header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.2rem 0 0 0;
}

.metadata-container {
    gap: 0.25rem;
    margin-top: 0;
    padding-bottom: 1rem;
    justify-content: space-between;
    align-items: center;
}

.language-chip-container {
    display: flex;
    gap: 0.25rem;
    align-items: center;
}

.add-language:hover {
    cursor: pointer;
}

.lifecycle-container {
    display: flex;
    flex-direction: column;
    align-items: end;
}

.add-language {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-primary-500);
    text-decoration: underline;
    padding: 0 0.5rem;
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
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-primary-500);
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
