<script setup lang="ts">
import { ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import { SCHEME_ICON, VIEW } from "@/arches_lingo/constants.ts";
import { fetchSchemeResource } from "@/arches_lingo/api.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { useResourceStore } from "@/arches_lingo/composables/useResourceStore.ts";

import type { DataComponentMode } from "@/arches_lingo/types.ts";
import type { Label, Labellable } from "@/arches_controlled_lists/types";

const props = defineProps<{
    mode: DataComponentMode;
    sectionTitle: string;
    componentName: string;
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId: string | undefined;
    tileId?: string;
}>();

const isLoading = ref(true);
const fetchError = ref();
const isTopConcept = ref(false);
const schemeId = ref<string>();
const schemeResource = ref<Labellable>();
const schemeLabel = ref<Label>();

const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());
const store = useResourceStore();
let initialized = false;

watch(
    [() => store.resource.value, () => store.error.value],
    async ([resource, storeError]) => {
        if (storeError) {
            fetchError.value = storeError;
            isLoading.value = false;
            return;
        }
        if (!resource || !props.resourceInstanceId || initialized) return;
        initialized = true;

        try {
            const topConceptOfTiles =
                resource.aliased_data?.top_concept_of ?? [];
            isTopConcept.value = topConceptOfTiles.length > 0;

            if (isTopConcept.value) {
                const resolvedSchemeId =
                    topConceptOfTiles[0]?.aliased_data?.top_concept_of
                        ?.details?.[0]?.resource_id;
                if (resolvedSchemeId) {
                    schemeId.value = resolvedSchemeId;
                    const fetchedScheme =
                        await fetchSchemeResource(resolvedSchemeId);
                    schemeResource.value = fetchedScheme;
                    schemeLabel.value = getItemLabel(
                        fetchedScheme,
                        selectedLanguage.value.code,
                        systemLanguage.value.code,
                    );
                }
            }
        } catch (error) {
            fetchError.value = error;
        } finally {
            isLoading.value = false;
        }
    },
    { immediate: true },
);

watch(
    () => selectedLanguage.value.code,
    (newCode) => {
        if (schemeResource.value) {
            schemeLabel.value = getItemLabel(
                schemeResource.value,
                newCode,
                systemLanguage.value.code,
            );
        }
    },
);
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
        v-else-if="isTopConcept && mode === VIEW"
        class="viewer-section"
    >
        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>
        </div>
        <div class="scheme-list">
            <RouterLink
                v-if="schemeLabel && schemeId"
                :to="{ name: routeNames.scheme, params: { id: schemeId } }"
                class="scheme-item"
            >
                <span :class="SCHEME_ICON"></span>
                <span class="scheme-label">{{ schemeLabel.value }}</span>
            </RouterLink>
        </div>
    </div>
</template>

<style scoped>
.scheme-list {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    padding-top: 0.5rem;
}

.scheme-item {
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

.scheme-item:hover {
    background: var(--p-highlight-background);
}

.scheme-label {
    color: var(--p-primary-500);
}
</style>
