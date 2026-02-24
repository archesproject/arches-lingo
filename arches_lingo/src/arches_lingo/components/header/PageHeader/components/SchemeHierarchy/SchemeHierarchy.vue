<script setup lang="ts">
import { ref } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import ProgressBar from "primevue/progressbar";

import ConceptTree from "@/arches_lingo/components/tree/ConceptTree.vue";

import { fetchConcepts } from "@/arches_lingo/api.ts";
import { ERROR, DEFAULT_ERROR_TOAST_LIFE } from "@/arches_lingo/constants.ts";

const props = withDefaults(
    defineProps<{
        isOpen?: boolean;
    }>(),
    {
        isOpen: true,
    },
);

const { $gettext } = useGettext();
const toast = useToast();

const concepts = ref();
const isRefreshing = ref(false);
let isInitialLoad = true;

const emit = defineEmits<{
    (e: "shouldShowHierarchy", value: boolean): void;
}>();

async function fetchAndSetConcepts() {
    if (!isInitialLoad) {
        isRefreshing.value = true;
    }
    try {
        concepts.value = await fetchConcepts();
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch concepts"),
            detail: (error as Error).message,
        });
    } finally {
        isRefreshing.value = false;
        isInitialLoad = false;
    }
}

fetchAndSetConcepts();

defineExpose({ refresh: fetchAndSetConcepts });
</script>

<template>
    <div class="hierarchy-header-container">
        <div class="hierarchy-header">
            <h2 class="title">
                {{ $gettext("Explore Hierarchies") }}
            </h2>

            <Button
                icon="pi pi-times"
                rounded
                text
                severity="contrast"
                :aria-label="$gettext('Close')"
                @click="emit('shouldShowHierarchy', false)"
            />
        </div>
    </div>
    <ProgressBar
        v-if="isRefreshing"
        mode="indeterminate"
        class="refresh-progress"
    />
    <ConceptTree
        :concepts="concepts"
        :is-open="props.isOpen"
    />
</template>

<style scoped>
.hierarchy-header-container {
    background: var(--p-header-toolbar-background);
}
.hierarchy-header {
    display: flex;
    width: 100%;
    justify-content: space-between;
    align-items: center;
    padding-inline-start: 1rem;
    padding-inline-end: 0.5rem;
}

.title {
    margin-top: 0px;
    margin-bottom: 0px;
    padding-top: 0.75rem;
    padding-bottom: 0.75rem;
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
}

.refresh-progress {
    height: 0.1875rem;
    border-radius: 0;
}
</style>
