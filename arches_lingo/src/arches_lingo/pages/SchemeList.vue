<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useGettext } from "vue3-gettext";

import Skeleton from "primevue/skeleton";

import { useToast } from "primevue/usetoast";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
} from "@/arches_controlled_lists/constants.ts";

import SchemeCard from "@/arches_lingo/components/scheme/SchemeCard.vue";
import { fetchLingoResources } from "@/arches_lingo/api.ts";
import { NEW } from "@/arches_lingo/constants.ts";

import type { ResourceInstanceResult } from "@/arches_lingo/types";

const toast = useToast();
const { $gettext } = useGettext();

const isLoading = ref(true);
const schemes = ref<ResourceInstanceResult[]>([]);

onMounted(async () => {
    try {
        schemes.value = await fetchLingoResources("scheme");
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch schemes"),
            detail: error instanceof Error ? error.message : undefined,
        });
    }

    schemes.value.unshift({
        resourceinstanceid: NEW,
        descriptors: {},
    });

    isLoading.value = false;
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
                v-for="scheme in schemes"
                :key="scheme.resourceinstanceid"
            >
                <SchemeCard :scheme="scheme" />
            </li>
        </ul>
    </div>
</template>

<style scoped>
.scheme-cards-container {
    padding: 0rem 1rem;
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
