<script setup lang="ts">
import { inject } from "vue";
import { systemLanguageKey } from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import Card from "primevue/card";

import type { Language } from "@/arches_vue_utils/types";
import type { SchemeResource, ResourceDescriptor } from "@/arches_lingo/types";

const systemLanguage = inject(systemLanguageKey) as Language;

const { scheme } = defineProps<{ scheme: SchemeResource }>();
const schemeURL = {
    name: routeNames.scheme,
    params: { id: scheme.resourceinstanceid },
};

const descriptors = scheme.descriptors;
let schemeDescriptor: ResourceDescriptor = {
    name: "",
    description: "",
};
if (descriptors) {
    const descriptor =
        descriptors[systemLanguage.code] ?? Object.values(descriptors)[0];
    schemeDescriptor.name = descriptor.name ?? "";
    schemeDescriptor.description = descriptor.description ?? "";
}
</script>

<template>
    <RouterLink :to="schemeURL">
        <Card>
            <template #title>
                {{ schemeDescriptor.name }}
            </template>
            <template #content>
                {{ schemeDescriptor.description }}
            </template>
        </Card>
    </RouterLink>
</template>

<style scoped>
a {
    text-decoration: none;
}

:deep(.p-card) {
    background-color: var(--p-button-primary-background);
    color: var(--p-button-primary-color);
    width: 15rem;
    height: 15rem;
    margin: 0.5rem;
}

:deep(.p-card-body) {
    text-align: center;
}
</style>
