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
                <div v-if="scheme.resourceinstanceid === NEW">
                    {{ $gettext("New Scheme") }}
                </div>
                <div
                    v-else
                    class="scheme-card"
                >
                    {{ schemeDescriptor.name }}
                </div>
            </template>
            <template #content>
                <div v-if="scheme.resourceinstanceid === NEW">
                    <div class="scheme-circle">
                        <i class="pi pi-share-alt new-scheme-icon"></i>
                    </div>
                </div>
                <span>{{ schemeDescriptor.description }}</span>
            </template>
            <template
                v-if="scheme.resourceinstanceid === NEW"
                #footer
            >
                <span>{{
                    $gettext("Add a new thesaurus, manage concept hierarchies")
                }}</span>
            </template>
        </Card>
    </RouterLink>
</template>

<style scoped>
ul:first-child li:first-child .p-card {
    color: var(--p-button-contrast-color);
    background: var(--p-arches-blue);
    border: 0.0625rem solid var(--p-surface-900);
}

ul:first-child li:first-child .p-card .scheme-circle {
    background: var(--p-blue-600);
}

a {
    text-decoration: none;
}

:deep(.p-card) {
    background-color: var(--p-button-primary-background);
    border: 0.0625rem solid var(--p-header-toolbar-border);
    color: var(--p-button-primary-color);
    width: 15rem;
    height: 15rem;
    margin: 0.25rem;
    border-radius: 0.125rem;
}

:deep(.p-card-body) {
    flex-grow: 1;
    text-align: center;
    overflow: hidden;
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
}

:deep(.p-card-content) {
    overflow: hidden;
    text-overflow: ellipsis;
}

:deep(.p-card-content > span),
:deep(.p-card-footer > span) {
    font-size: var(--p-lingo-font-size-xsmall);
}

.scheme-circle {
    display: inline-block;
    text-align: center;
    padding: 1.25rem;
    margin: 1rem;
    border-radius: 50%;
    background: var(--p-surface-400);
    border: 0.0625rem solid var(--p-surface-900);
}

.new-scheme-icon {
    font-size: var(--p-lingo-font-size-xxlarge);
}
</style>
