<script setup lang="ts">
import { inject, onMounted, ref, watch } from "vue";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";

import { fetchLingoResource } from "@/arches_lingo/api.ts";
import { extractDescriptors } from "@/arches_lingo/utils.ts";

import type {
    ResourceInstanceResult,
    SchemeHeader,
} from "@/arches_lingo/types";
import type { Language } from "@/arches_vue_utils/types";

const toast = useToast();
const { $gettext } = useGettext();
const systemLanguage = inject(systemLanguageKey) as Language;

const scheme = ref<ResourceInstanceResult>();

const props = defineProps<{
    sectionTitle: string;
    componentName: string;
    graphSlug: string;
    resourceInstanceId: string;
}>();

const data = ref<SchemeHeader>();
watch(
    () => scheme.value,
    (newValue) => {
        const descriptor = extractDescriptors(newValue, systemLanguage);
        const principalUser = newValue?.principalUser;
        const lifeCycleState = newValue?.resource_instance_lifecycle_state;

        data.value = {
            descriptor: descriptor,
            principalUser: principalUser,
            lifeCycleState: lifeCycleState,
        };
    },
);

onMounted(async () => {
    try {
        scheme.value = await fetchLingoResource(
            props.graphSlug,
            props.resourceInstanceId,
        );
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch scheme"),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
});
</script>

<template>
    <div>
        <h2>{{ data?.descriptor?.name }} ({{ systemLanguage.name }})</h2>
        <p>Description: {{ data?.descriptor?.description }}</p>
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
