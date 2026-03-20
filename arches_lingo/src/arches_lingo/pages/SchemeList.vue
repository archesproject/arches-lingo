<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useGettext } from "vue3-gettext";
import { storeToRefs } from "pinia";

import Skeleton from "primevue/skeleton";

import { useToast } from "primevue/usetoast";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
} from "@/arches_controlled_lists/constants.ts";

import SchemeCard from "@/arches_lingo/components/scheme/SchemeCard.vue";
import { fetchLingoResources } from "@/arches_lingo/api.ts";
import { NEW } from "@/arches_lingo/constants.ts";
import { sortItemsByLabel } from "@/arches_lingo/utils.ts";
import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

import type { Scheme, SchemeStatement } from "@/arches_lingo/types";

const toast = useToast();
const { $gettext } = useGettext();
const { isEditor } = useUserStore();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());
const conceptStore = useConceptStore();

const isLoading = ref(true);
const schemes = ref<Scheme[]>([]);
const statementsMap = ref<Map<string, SchemeStatement[]>>(new Map());

onMounted(async () => {
    try {
        await conceptStore.initialize();
        buildSchemeList();
    } finally {
        isLoading.value = false;
    }

    fetchStatements();
});

const schemeEntries = computed(() =>
    sortItemsByLabel(
        schemes.value,
        selectedLanguage.value.code,
        systemLanguage.value.code,
        true,
        NEW,
    ).map((scheme) => ({
        scheme,
        statements: statementsMap.value.get(scheme.id),
    })),
);

function buildSchemeList() {
    schemes.value = [...conceptStore.schemes];
    if (isEditor && !schemes.value.some((scheme) => scheme.id === NEW)) {
        schemes.value.unshift({ id: NEW, labels: [], top_concepts: [] });
    }
}

async function fetchStatements() {
    try {
        const resources = await fetchLingoResources("scheme");
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
}

async function fetchSchemes() {
    isLoading.value = true;
    statementsMap.value = new Map();

    try {
        await conceptStore.refresh();
        buildSchemeList();
    } finally {
        isLoading.value = false;
    }

    fetchStatements();
}
</script>

<template>
    <Skeleton
        v-if="isLoading"
        class="loading-skeleton"
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
.loading-skeleton {
    width: 100%;
    height: 100%;
}

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
