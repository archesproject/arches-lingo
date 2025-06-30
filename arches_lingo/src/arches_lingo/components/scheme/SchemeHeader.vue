<script setup lang="ts">
import { inject, onMounted, ref } from "vue";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import Skeleton from "primevue/skeleton";

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
    <Skeleton
        v-if="isLoading"
        style="width: 100%"
    />

    <div
        v-else
        class="scheme-header"
    >
        <div class="scheme-header-panel">
            <div class="header-row">
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

                <!-- TODO: export to rdf/skos/json-ld buttons go here -->
                <div class="header-item">
                    <span class="header-item-label">
                        {{ $gettext("Export:") }}
                    </span>
                    <span class="header-item-value">
                        CSV | SKOS | RDF | JSON-LD
                    </span>
                </div>
            </div>

            <!-- TODO: show Scheme URI here -->
            <div class="header-row uri-container">
                <span class="header-item-label">{{ $gettext("URI:") }}</span>
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
                            {{ data?.principalUser || $gettext("Anonymous") }}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.scheme-header {
    padding: 1rem 1rem 1.25rem 1rem;
    background: var(--p-header-background);
    border-bottom: 0.06rem solid var(--p-header-border);
}

.scheme-header-panel {
    padding-bottom: 0.5rem;
}

h2 {
    margin: 0;
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
}

.scheme-label-lang {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
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
    margin-top: 0.5rem;
    justify-content: space-between;
    align-items: center;
}

.language-chip-container {
    display: flex;
    gap: 0.25rem;
    align-items: center;
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
    margin-inline-end: 1rem;
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
    border: 0.06rem solid var(--p-menubar-item-icon-color);
    border-radius: 0.125rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-content-color);
}
</style>
