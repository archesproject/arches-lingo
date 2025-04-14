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

import type { ResourceInstanceResult } from "@/arches_lingo/types";
import type { Language } from "@/arches_vue_utils/types";

const toast = useToast();
const { $gettext } = useGettext();
const systemLanguage = inject(systemLanguageKey) as Language;

const scheme = ref<ResourceInstanceResult>();

const props = defineProps<{
    // mode: DataComponentMode;
    sectionTitle: string;
    componentName: string;
    graphSlug: string;
    // nodegroupAlias: string;
    resourceInstanceId: string;
    // tileId?: string;
}>();

const schemeDescriptor = ref();
watch(
    () => scheme.value,
    (newValue) => {
        schemeDescriptor.value = extractDescriptors(newValue, systemLanguage);
    },
);

onMounted(async () => {
    try {
        scheme.value = await fetchLingoResource(
            "scheme",
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
        <h2>{{ schemeDescriptor?.name }} ({{ systemLanguage.name }})</h2>
        <p>URI:</p>
        <p>Description: {{ schemeDescriptor?.description }}</p>
        <p>Life cycle state:</p>
        <p>Created by:</p>
    </div>
</template>

<style scoped>
p {
    margin: 0;
}
</style>
