<script setup lang="ts">
import { ref, watchEffect } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";

import ConceptTree from "@/arches_lingo/components/tree/ConceptTree.vue";

import { fetchConcepts } from "@/arches_lingo/api.ts";
import { ERROR, DEFAULT_ERROR_TOAST_LIFE } from "@/arches_lingo/constants.ts";

const { $gettext } = useGettext();
const toast = useToast();

const conceptTreeKey = ref(0);
const concepts = ref();

const emit = defineEmits<{
    (e: "shouldShowHierarchy", value: boolean): void;
}>();

watchEffect(async () => {
    try {
        concepts.value = await fetchConcepts();
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch concepts"),
            detail: (error as Error).message,
        });
    }
});
</script>

<template>
    <div
        style="
            display: flex;
            width: 100%;
            justify-content: space-between;
            align-items: center;
            padding: 0 0.75rem;
        "
    >
        <h2>{{ $gettext("Explore Hierarchies") }}</h2>

        <Button
            icon="pi pi-times"
            rounded
            text
            severity="contrast"
            :aria-label="$gettext('Close')"
            @click="emit('shouldShowHierarchy', false)"
        />
    </div>

    <ConceptTree
        :key="conceptTreeKey"
        :concepts="concepts"
    />
</template>
