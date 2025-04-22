<script setup lang="ts">
import { inject, onMounted, ref } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Divider from "primevue/divider";
import ProgressSpinner from "primevue/progressspinner";

import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    systemLanguageKey,
    VIEW,
} from "@/arches_lingo/constants.ts";

import { fetchLingoResource } from "@/arches_lingo/api.ts";
import { extractDescriptors } from "@/arches_lingo/utils.ts";

import type {
    ConceptHeaderData,
    ConceptClassificationStatusAliases,
    ResourceInstanceResult,
    DataComponentMode,
} from "@/arches_lingo/types.ts";

import type { Language } from "@/arches_vue_utils/types.ts";

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

const concept = ref<ResourceInstanceResult>();
const data = ref<ConceptHeaderData>();
const isLoading = ref(true);

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
</script>

<template>
    <ProgressSpinner
        v-if="isLoading"
        style="width: 100%"
    />
    <div v-else>
        <div class="header-row">
            <h2>
                {{ data?.descriptor?.name }} ({{ data?.descriptor?.language }})
            </h2>
            <!-- TODO: Life Cycle mgmt functionality goes here -->
            <div class="header-item">
                <span class="header-item-label">{{
                    $gettext("Life cycle state:")
                }}</span>
                <span>{{ data?.lifeCycleState }}</span>
            </div>
        </div>
        <div class="header-row">
            <div class="header-item">
                <span class="header-item-label">{{ $gettext("URI:") }}</span>
                <Button
                    :label="data?.uri || '--'"
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
                <span class="header-item-label">{{ $gettext("Scheme:") }}</span>
                <!-- TODO: Allow resource multiselect to route within lingo, not to resource pg -->
                <ResourceInstanceMultiSelectWidget
                    :graph-slug="props.graphSlug"
                    node-alias="part_of_scheme"
                    :initial-value="data?.partOfScheme"
                    :mode="VIEW"
                    :show-label="false"
                ></ResourceInstanceMultiSelectWidget>
            </div>
            <!-- TODO: export to rdf/skos/json-ld buttons go here -->
        </div>
        <div class="header-row">
            <div class="header-item">
                <span class="header-item-label">{{
                    $gettext("Parent Concept(s):")
                }}</span>
                <!-- TODO: Allow resource multiselect to route within lingo, not to resource pg -->
                <ResourceInstanceMultiSelectWidget
                    :graph-slug="props.graphSlug"
                    node-alias="classification_status_ascribed_classification"
                    :initial-value="data?.parentConcepts"
                    :mode="VIEW"
                    :show-label="false"
                ></ResourceInstanceMultiSelectWidget>
            </div>
            <div class="header-item">
                <span class="header-item-label">{{ $gettext("Owner:") }}</span>
                <span>{{ data?.principalUser || $gettext("Anonymous") }}</span>
            </div>
        </div>
        <Divider />
    </div>
</template>

<style scoped>
h2 {
    margin-bottom: 1rem;
}
.p-button-link {
    padding: 0;
    margin: 0;
}
.header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.header-item {
    display: inline-flex;
    margin-inline-end: 1rem;
}
.header-item-label {
    font-weight: bold;
    margin-inline-end: 0.25rem;
}
</style>
