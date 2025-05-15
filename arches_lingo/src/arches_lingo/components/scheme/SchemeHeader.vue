<script setup lang="ts">
import { inject, onMounted, ref } from "vue";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import Divider from "primevue/divider";
import ProgressSpinner from "primevue/progressspinner";

import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";

import { fetchLingoResource } from "@/arches_lingo/api.ts";
import { extractDescriptors } from "@/arches_lingo/utils.ts";

import type {
    DataComponentMode,
    ResourceInstanceResult,
    SchemeHeader,
} from "@/arches_lingo/types.ts";
import type { Language } from "@/arches_component_lab/types.ts";

const props = defineProps<{
    mode: DataComponentMode;
    sectionTitle: string;
    componentName: string;
    graphSlug: string;
    resourceInstanceId: string | undefined;
    nodegroupAlias: string;
}>();

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
</script>

<template>
    <ProgressSpinner
        v-if="isLoading"
        style="width: 100%"
    />

    <div class="scheme-header" v-else>
        <div class="scheme-header-panel">
            <div class="header-row">
                <h2>
                    {{ data?.descriptor?.name }}  <span class="scheme-label-lang">({{ data?.descriptor?.language }})</span>
                </h2>

                <!-- TODO: export to rdf/skos/json-ld buttons go here -->
                <div class="header-item">
                    <span class="header-item-label">{{
                        $gettext("Export:")
                    }}</span>
                    <span class="header-item-value">CSV | SKOS | RDF | JSON-LD</span>
                </div>
            </div>

            <!-- TODO: show Scheme URI here -->
            <div class="header-row uri-container">
                <span class="header-item-label">{{ $gettext("URI:") }}</span>
            </div>

            <div class="header-row metadata-container">

                <!-- TODO: Load Scheme languages here -->
                <div class="language-chip-container">
                    <span class="scheme-language">{{ $gettext("English (en)") }}</span>
                    <span class="scheme-language">{{ $gettext("German (de)") }}</span>
                    <span class="scheme-language">{{ $gettext("French (fr)") }}</span>
                    <span class="add-language">{{ $gettext("Add Language") }}</span>
                </div>
                
                <div class="lifecycle-container">
                    <div class="header-item">
                        <span class="header-item-label">{{
                            $gettext("Life cycle state:")
                        }}</span>
                        <span class="header-item-value">{{ data?.lifeCycleState }}</span>
                    </div>
                    <div class="header-item" style="padding-top: .1rem;">
                        <span class="header-item-label">{{ $gettext("Owner:") }}</span>
                        <span class="header-item-value">{{ data?.principalUser || $gettext("Anonymous") }}</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.scheme-header {
    padding: 1rem 1rem 1.25rem 1rem;
    background: var(--p-slate-50);
    border-bottom: 1px solid var(--p-neutral-300);
}

.scheme-header-panel {
    padding-bottom: 0.5rem;
}

h2 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 400;
}

.scheme-label-lang {
    font-size: .9rem;
    color: var(--p-slate-400);
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
.uri-container {
    justify-content: flex-start;
}
.metadata-container {
    gap: 0.25rem;
    margin-top: .5rem;
    justify-content: space-between;
    align-items: anchor-center;
}
.language-chip-container {
    display: flex; gap: .25rem; 
    align-items: center;
}
.lifecycle-container {
    display: flex; 
    flex-direction: column;
    align-items: end;
}
.add-language {
    font-size: .9rem;
    color: var(--p-primary-500);
    text-decoration: underline;
    padding: 0 .5rem;
}
.header-item {
    display: inline-flex;
    margin-inline-end: 1rem;
    align-items: baseline;
}
.header-item-label {
    font-weight: 400;
    font-size: .9rem;
    color: var(--p-slate-500);
    margin-inline-end: 0.25rem;
}
.header-item-value {
    font-size: .9rem;
    color: var(--p-primary-500);
}

.scheme-language {
    padding: 0.5rem 1rem;
    background: var(--p-menubar-item-icon-color);
    border: 1px solid var(--p-menubar-item-icon-color);
    border-radius: 2px;
    font-size: .9rem;
    color: var(--p-content-color);
}
</style>
