<script setup lang="ts">
import { inject, onMounted, ref } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Select from "primevue/select";

import LingoResourceHeader from "@/arches_lingo/components/header/LingoResourceHeader/LingoResourceHeader.vue";

import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";

import { fetchLingoResource } from "@/arches_lingo/api.ts";
import { extractDescriptors } from "@/arches_lingo/utils.ts";

import type {
    ConceptClassificationStatusAliases,
    DataComponentMode,
    IdentifierAliases,
    ResourceInstanceResult,
    ResourceHeaderData,
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

const concept = ref<ResourceInstanceResult>();
const data = ref<ResourceHeaderData>();
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
    const identifier = concept?.aliased_data?.identifier.map(
        (value: IdentifierAliases) => {
            return value.aliased_data?.identifier_content?.node_value;
        },
    );
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
        identifier: identifier,
        partOfScheme: partOfScheme,
        parentConcepts: parentConcepts,
    };
}
</script>

<template>
    <LingoResourceHeader
        v-if="concept && data"
        :resource="concept"
        :header-data="data"
        :section-title="props.sectionTitle"
        :graph-slug="props.graphSlug"
        :nodegroup-alias="props.nodegroupAlias"
        :is-loading="isLoading"
    >
        <template #controls>
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

            <div class="header-buttons">
                <Button
                    icon="pi pi-plus-circle"
                    :label="$gettext('Add Child')"
                    class="add-button"
                ></Button>
            </div>
        </template>
    </LingoResourceHeader>
</template>

<style scoped>
.p-select {
    margin: 0rem 0.5rem;
    border-radius: 0.125rem;
    box-shadow: none;
    width: 10rem;
}

.delete-button {
    font-size: var(--p-lingo-font-size-small);
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
</style>
