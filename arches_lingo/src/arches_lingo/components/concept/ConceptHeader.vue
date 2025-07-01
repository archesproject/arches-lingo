<script setup lang="ts">
import { inject, onMounted, ref } from "vue";

import { useConfirm } from "primevue/useconfirm";
import { useGettext } from "vue3-gettext";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";

import ConfirmDialog from "primevue/confirmdialog";
import Button from "primevue/button";
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
        <div class="header-row">
            <h2 v-if="data?.descriptor?.name">
                <Button
                    icon="pi pi-trash"
                    severity="danger"
                    rounded
                    style="margin-inline-end: 0.75rem"
                    :aria-label="$gettext('Delete Concept')"
                    @click="confirmDelete"
                />
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

        <div class="concept-header-section">
            <div class="header-row uri-container">
                <span class="header-item-label">{{ $gettext("URI:") }}</span>
                <Button
                    :label="data?.uri || '--'"
                    class="concept-uri"
                    variant="link"
                    as="a"
                    :href="data?.uri"
                    target="_blank"
                    rel="noopener"
                    :disabled="!data?.uri"
                ></Button>
            </div>
            <div class="header-row">
                <!-- TODO: Human-reable conceptid to be displayed here -->
                <div class="header-item">
                    <span class="header-item-label">
                        {{ $gettext("Scheme:") }}
                    </span>
                    <span class="header-item-value">
                        <RouterLink
                            :to="`/scheme/${data?.partOfScheme?.interchange_value}`"
                            >{{ data?.partOfScheme?.display_value }}</RouterLink
                        >
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
</template>

<style scoped>
.concept-header {
    padding-inline-start: 1rem;
    padding-inline-end: 1.5rem;
    padding-bottom: 1rem;
    background: var(--p-header-background);
    border-bottom: 0.06rem solid var(--p-header-border);
}

h2 {
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
}

.concept-label-lang {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
}

.concept-uri {
    font-size: var(--p-lingo-font-size-xsmall);
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

.uri-container {
    justify-content: flex-start;
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

.header-item-value,
:deep(a) {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-primary-500);
}

.parent-concept {
    margin-inline-end: 0.5rem;
}
</style>
