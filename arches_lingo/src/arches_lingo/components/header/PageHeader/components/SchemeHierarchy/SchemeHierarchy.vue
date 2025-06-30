<script setup lang="ts">
import { ref, watchEffect } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Drawer from "primevue/drawer";

import ConceptTree from "@/arches_lingo/components/tree/ConceptTree.vue";

import { fetchConcepts } from "@/arches_lingo/api.ts";
import { ERROR, DEFAULT_ERROR_TOAST_LIFE } from "@/arches_lingo/constants.ts";

const { $gettext } = useGettext();
const toast = useToast();

const showHierarchy = ref(false);
const conceptTreeKey = ref(0);
const concepts = ref();

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
    <div>
        <Button
            icon="pi pi-globe"
            variant="text"
            class="explore-button"
            :label="$gettext('Explore')"
            @click="showHierarchy = true"
        />
        <Drawer
            v-model:visible="showHierarchy"
            class="hierarchy-container"
            style="min-width: 32rem"
            :header="$gettext('Explore Hierarchies')"
            :pt="{
                content: {
                    style: {
                        padding: '0',
                        display: 'flex',
                        flexDirection: 'column',
                        fontFamily: 'var(--p-lingo-font-family)',
                    },
                },
                header: {
                    style: {
                        display: 'flex',
                        justifyContent: 'space-between',
                        backgroundColor:
                            'var(--p-form-field-filled-background)',
                        paddingBottom: '0.5rem',
                        fontFamily: 'var(--p-lingo-font-family)',
                    },
                },
            }"
        >
            <ConceptTree
                :key="conceptTreeKey"
                :concepts="concepts"
            />
        </Drawer>
    </div>
</template>

<style scoped>
.explore-button {
    color: var(--p-menubar-text-color) !important;
}

.explore-button:hover {
    background: var(--p-button-primary-hover-background) !important;
}
</style>
