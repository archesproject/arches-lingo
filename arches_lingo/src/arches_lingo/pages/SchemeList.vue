<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useGettext } from "vue3-gettext";

import Skeleton from "primevue/skeleton";

import { useToast } from "primevue/usetoast";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
} from "@/arches_controlled_lists/constants.ts";

import SchemeCard from "@/arches_lingo/components/scheme/SchemeCard.vue";
import { fetchConcepts, fetchLingoResources } from "@/arches_lingo/api.ts";
import { NEW } from "@/arches_lingo/constants.ts";
import { useLingoUser } from "@/arches_lingo/composables/useLingoUser.ts";

import type { Scheme, SchemeStatement } from "@/arches_lingo/types";

const toast = useToast();
const { $gettext } = useGettext();
const { isEditor } = useLingoUser();

const isLoading = ref(true);
const schemes = ref<Scheme[]>([]);
const statementsMap = ref<Map<string, SchemeStatement[]>>(new Map());

async function fetchSchemes() {
    schemes.value = [];
    statementsMap.value = new Map();
    isLoading.value = true;
    try {
        const [concepts, resources] = await Promise.all([
            fetchConcepts(),
            fetchLingoResources("scheme"),
        ]);
        schemes.value = concepts.schemes as Scheme[];

        const schemeStatementMap = new Map<string, SchemeStatement[]>();
        for (const resource of resources) {
            const statements = resource.aliased_data?.statement;
            if (statements) {
                schemeStatementMap.set(resource.resourceinstanceid, statements);
            }
        }
        statementsMap.value = schemeStatementMap;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch schemes"),
            detail: error instanceof Error ? error.message : undefined,
        });
    }

    if (isEditor.value) {
        schemes.value.unshift({
            id: NEW,
            labels: [],
            top_concepts: [],
        });
    }

    isLoading.value = false;
}

const schemeEntries = computed(() =>
    schemes.value.map((scheme) => ({
        scheme,
        statements: statementsMap.value.get(scheme.id),
    })),
);

onMounted(async () => {
    await fetchSchemes();
});
</script>

<template>
    <Skeleton
        v-if="isLoading"
        style="margin: 1rem; height: 2rem"
    />
    <Skeleton
        v-if="isLoading"
        style="margin: 1rem; height: 2rem"
    />
    <Skeleton
        v-if="isLoading"
        style="margin: 1rem; height: 2rem"
    />
    <Skeleton
        v-if="isLoading"
        style="margin: 1rem; height: 2rem"
    />
    <Skeleton
        v-if="isLoading"
        style="margin: 1rem; height: 2rem"
    />
    <Skeleton
        v-if="isLoading"
        style="margin: 1rem; height: 2rem"
    />
    <Skeleton
        v-if="isLoading"
        style="margin: 1rem; height: 2rem"
    />

    <div class="scheme-cards-container">
        <ul class="scheme-cards">
            <li
                v-for="{ scheme, statements } in schemeEntries"
                :key="scheme.id"
            >
                <SchemeCard
                    :scheme="scheme"
                    :statements="statements"
                    @imported="fetchSchemes"
                />
            </li>
        </ul>
    </div>
</template>

<style scoped>
.scheme-cards-container {
    padding: 0rem 1rem;
    height: 100%;
    overflow: auto;
}
.scheme-cards {
    display: flex;
    flex-wrap: wrap;
    list-style-type: none;
    padding: 0;
}

.scheme-cards .p-card:first-child {
    background: var(--p-scheme-circle-background);
}
</style>
