<script setup lang="ts">
import { ref, watch } from "vue";
import { storeToRefs } from "pinia";

import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import { VIEW } from "@/arches_lingo/constants.ts";
import { fetchSchemeResource } from "@/arches_lingo/api.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
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
                const schemeId =
                    topConceptOfTiles[0]?.aliased_data?.top_concept_of
                        ?.details?.[0]?.resource_id;
                if (schemeId) {
                    const fetchedScheme = await fetchSchemeResource(schemeId);
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
    <template v-else-if="isTopConcept && mode === VIEW">
        <div
            class="viewer-section"
            style="padding-bottom: 0"
        >
            <div class="section-header">
                <h2>{{ props.sectionTitle }}</h2>
            </div>
            <div class="top-concept-info">
                <span v-if="schemeLabel">{{ schemeLabel.value }}</span>
            </div>
        </div>
    </template>
</template>

<style scoped>
.top-concept-info {
    margin-inline-start: 1rem;
    margin-top: 1rem;
    margin-bottom: 1rem;
    font-size: var(--p-lingo-font-size-smallnormal);
}
</style>
