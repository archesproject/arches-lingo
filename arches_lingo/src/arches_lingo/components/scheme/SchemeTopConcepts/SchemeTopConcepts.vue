<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useGettext } from "vue3-gettext";
import { RouterLink } from "vue-router";
import { useToast } from "primevue/usetoast";
import { storeToRefs } from "pinia";

import Skeleton from "primevue/skeleton";
import Message from "primevue/message";

import { fetchSchemeTopConcepts } from "@/arches_lingo/api.ts";
import { getConceptIcon } from "@/arches_lingo/utils.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";

import type { Concept, DataComponentMode } from "@/arches_lingo/types.ts";

const props = defineProps<{
    mode: DataComponentMode;
    sectionTitle: string;
    componentName: string;
    graphSlug: string;
    resourceInstanceId: string | undefined;
    nodegroupAlias: string;
}>();

const { $gettext } = useGettext();
const toast = useToast();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

const topConcepts = ref<Concept[]>([]);
const isLoading = ref(true);
const fetchError = ref<Error>();

const sortedTopConcepts = computed(() => {
    return [...topConcepts.value].sort((conceptA, conceptB) => {
        const labelA = getItemLabel(
            conceptA,
            selectedLanguage.value.code,
            systemLanguage.value.code,
        ).value.toLowerCase();
        const labelB = getItemLabel(
            conceptB,
            selectedLanguage.value.code,
            systemLanguage.value.code,
        ).value.toLowerCase();
        return labelA.localeCompare(labelB);
    });
});

onMounted(async () => {
    if (!props.resourceInstanceId) {
        isLoading.value = false;
        return;
    }

    try {
        const schemeData = await fetchSchemeTopConcepts(
            props.resourceInstanceId,
        );
        topConcepts.value = schemeData.top_concepts;
    } catch (error) {
        fetchError.value =
            error instanceof Error ? error : new Error(String(error));
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch top concepts"),
            detail: fetchError.value.message,
        });
    } finally {
        isLoading.value = false;
    }
});
</script>

<template>
    <Skeleton
        v-if="isLoading"
        style="width: 100%"
    />
    <Message
        v-else-if="fetchError"
        severity="error"
        size="small"
    >
        {{ fetchError.message }}
    </Message>
    <div
        v-else
        class="viewer-section"
    >
        <div class="section-header">
            <h2>{{ sectionTitle }}</h2>
        </div>
        <div
            v-if="topConcepts.length"
            class="top-concepts-list"
        >
            <RouterLink
                v-for="concept in sortedTopConcepts"
                :key="concept.id"
                :to="{
                    name: routeNames.concept,
                    params: { id: concept.id },
                }"
                class="top-concept-item"
            >
                <span :class="getConceptIcon(concept)"></span>
                <span class="top-concept-label">
                    {{
                        getItemLabel(
                            concept,
                            selectedLanguage.code,
                            systemLanguage.code,
                        ).value
                    }}
                </span>
            </RouterLink>
        </div>
        <div
            v-else
            class="section-message"
        >
            {{ $gettext("No top concepts found.") }}
        </div>
    </div>
</template>

<style scoped>
.top-concepts-list {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    padding-top: 0.5rem;
}

.top-concept-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0.5rem;
    border-radius: 0.25rem;
    cursor: pointer;
    font-size: var(--p-lingo-font-size-smallnormal);
    text-decoration: none;
    color: inherit;
}

.top-concept-item:hover {
    background: var(--p-highlight-background);
}

.top-concept-label {
    color: var(--p-primary-500);
}
</style>
