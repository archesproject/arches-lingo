<script setup lang="ts">
import { inject, onMounted, ref, watch } from "vue";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    systemLanguageKey,
    VIEW,
} from "@/arches_lingo/constants.ts";

import { fetchLingoResource } from "@/arches_lingo/api.ts";
import { extractDescriptors } from "@/arches_lingo/utils.ts";

import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

import type {
    ConceptHeader,
    ConceptClassificationStatusAliases,
    ResourceInstanceResult,
} from "@/arches_lingo/types";
import type { Language } from "@/arches_vue_utils/types";

const toast = useToast();
const { $gettext } = useGettext();
const systemLanguage = inject(systemLanguageKey) as Language;

const concept = ref<ResourceInstanceResult>();

const props = defineProps<{
    sectionTitle: string;
    componentName: string;
    graphSlug: string;
    resourceInstanceId: string;
}>();

const data = ref<ConceptHeader>();

watch(
    () => concept.value,
    (newValue) => {
        const aliased_data = newValue?.aliased_data;

        const descriptor = extractDescriptors(newValue, systemLanguage);
        const principalUser = newValue?.principalUser;
        const lifeCycleState = newValue?.resource_instance_lifecycle_state;
        const uri = aliased_data?.uri?.aliased_data?.uri_content?.url;
        const partOfScheme =
            aliased_data?.part_of_scheme?.aliased_data?.part_of_scheme;
        const parentConcepts = (
            aliased_data?.classification_status || []
        ).flatMap(
            (tile: ConceptClassificationStatusAliases) =>
                tile?.aliased_data
                    ?.classification_status_ascribed_classification || [],
        );

        data.value = {
            descriptor: descriptor,
            uri: uri,
            principalUser: principalUser,
            lifeCycleState: lifeCycleState,
            partOfScheme: partOfScheme,
            parentConcepts: parentConcepts,
        };
    },
);

onMounted(async () => {
    try {
        concept.value = await fetchLingoResource(
            props.graphSlug,
            props.resourceInstanceId,
        );
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch concept"),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
});
</script>

<template>
    <div>
        <h2>{{ data?.descriptor?.name }} ({{ systemLanguage.name }})</h2>
        <p>
            URI:
            <a
                :href="data?.uri"
                target="_blank"
                rel="noopener noreferrer"
                >{{ data?.uri }}</a
            >
        </p>
        <p>
            Scheme:
            <ResourceInstanceMultiSelectWidget
                :graph-slug="props.graphSlug"
                node-alias="part_of_scheme"
                :initial-value="data?.partOfScheme"
                :mode="VIEW"
                :show-label="false"
            ></ResourceInstanceMultiSelectWidget>
        </p>
        <p>
            Parent Concept(s):
            <ResourceInstanceMultiSelectWidget
                :graph-slug="props.graphSlug"
                node-alias="classification_status_ascribed_classification"
                :initial-value="data?.parentConcepts"
                :mode="VIEW"
                :show-label="false"
            ></ResourceInstanceMultiSelectWidget>
        </p>
        <p>Life cycle state: {{ data?.lifeCycleState }}</p>
        <p>
            Created by:
            {{ data?.principalUser || $gettext("No Principal User") }}
        </p>
    </div>
</template>

<style scoped>
p {
    margin: 0;
}
</style>
