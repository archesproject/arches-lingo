<script setup lang="ts">
import { inject } from "vue";
import { systemLanguageKey, NEW } from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import Card from "primevue/card";

import { extractDescriptors } from "@/arches_lingo/utils.ts";

import type { Language } from "@/arches_component_lab/types";
import type { ResourceInstanceResult } from "@/arches_lingo/types";

const systemLanguage = inject(systemLanguageKey) as Language;

const { scheme } = defineProps<{ scheme: ResourceInstanceResult }>();
const schemeURL = {
    name: routeNames.scheme,
    params: { id: scheme.resourceinstanceid },
};

const schemeDescriptor = extractDescriptors(scheme, systemLanguage);
</script>

<template>
    <RouterLink :to="schemeURL">
        <Card>
            <template #title>
                <p v-if="scheme.resourceinstanceid === NEW">
                    {{ $gettext("Create a new scheme") }}
                </p>
                <p v-else>{{ schemeDescriptor.name }}</p>
            </template>
            <template #content>
                <p>{{ schemeDescriptor.description }}</p>
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
    flex-grow: 1;
    text-align: center;
    overflow: hidden;
}

:deep(.p-card-content) {
    overflow: hidden;
    text-overflow: ellipsis;
}

:deep(.p-card-content > p) {
    margin: 0;
}
</style>
