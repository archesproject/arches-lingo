<script setup lang="ts">
import { ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import ConceptSetList from "@/arches_lingo/components/concept-set-browser/components/ConceptSetList.vue";
import ConceptSetMemberList from "@/arches_lingo/components/concept-set-browser/components/ConceptSetMemberList.vue";

import {
    fetchConceptSets,
    fetchConceptSetDetail,
    createConceptSet,
    deleteConceptSet,
    addToConceptSet,
    removeFromConceptSet,
} from "@/arches_lingo/api.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    ERROR,
    SUCCESS,
} from "@/arches_lingo/constants.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

import type { ConceptSetDetail, ConceptSetItem } from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();
const toast = useToast();
const { isAnonymous } = storeToRefs(useUserStore());

const conceptSets = ref<ConceptSetItem[]>([]);
const activeSetDetail = ref<ConceptSetDetail | null>(null);

async function loadConceptSets() {
    try {
        const result = await fetchConceptSets();
        conceptSets.value = result.data;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to load concept sets."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

async function handleSelectSet(setItem: ConceptSetItem) {
    try {
        activeSetDetail.value = await fetchConceptSetDetail(setItem.id);
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to load concept set."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

function handleBackToList() {
    activeSetDetail.value = null;
}

async function handleCreateSet(name: string, description: string) {
    try {
        const created = await createConceptSet(name, description);
        conceptSets.value.unshift(created);
        toast.add({
            severity: SUCCESS,
            life: DEFAULT_TOAST_LIFE,
            summary: $gettext("Concept set created."),
        });
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to create concept set."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

async function handleDeleteSet(setItem: ConceptSetItem) {
    try {
        await deleteConceptSet(setItem.id);
        conceptSets.value = conceptSets.value.filter(
            (existingSet) => existingSet.id !== setItem.id,
        );
        toast.add({
            severity: SUCCESS,
            life: DEFAULT_TOAST_LIFE,
            summary: $gettext("Concept set deleted."),
        });
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to delete concept set."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

async function handleAddCurrentConcept(conceptId: string) {
    if (!activeSetDetail.value) return;
    const setId = activeSetDetail.value.id;
    try {
        const result = await addToConceptSet(setId, [conceptId]);
        activeSetDetail.value = await fetchConceptSetDetail(setId);
        const matchingSetInList = conceptSets.value.find(
            (existingSet) => existingSet.id === setId,
        );
        if (matchingSetInList) {
            matchingSetInList.member_count = result.member_count;
        }
        toast.add({
            severity: SUCCESS,
            life: DEFAULT_TOAST_LIFE,
            summary: $gettext("Concept added to set."),
        });
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to add concept to set."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

async function handleRemoveMembers(conceptIds: string[]) {
    if (!activeSetDetail.value) return;
    const setId = activeSetDetail.value.id;
    try {
        const result = await removeFromConceptSet(setId, conceptIds);
        activeSetDetail.value = await fetchConceptSetDetail(setId);
        const matchingSetInList = conceptSets.value.find(
            (existingSet) => existingSet.id === setId,
        );
        if (matchingSetInList) {
            matchingSetInList.member_count = result.member_count;
        }
        toast.add({
            severity: SUCCESS,
            life: DEFAULT_TOAST_LIFE,
            summary: $gettext("%{count} concepts removed from set.", {
                count: String(conceptIds.length),
            }),
        });
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to remove concepts from set."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

watch(
    isAnonymous,
    (newIsAnonymous) => {
        if (!newIsAnonymous) {
            loadConceptSets();
        }
    },
    { immediate: true },
);
</script>

<template>
    <div class="concept-set-browser">
        <ConceptSetMemberList
            v-if="activeSetDetail !== null"
            :set-detail="activeSetDetail"
            @back="handleBackToList"
            @remove-members="handleRemoveMembers"
            @add-current-concept="handleAddCurrentConcept"
        />
        <ConceptSetList
            v-else
            :concept-sets="conceptSets"
            @select-set="handleSelectSet"
            @create-set="handleCreateSet"
            @delete-set="handleDeleteSet"
        />
    </div>
</template>

<style scoped>
.concept-set-browser {
    height: 100%;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}
</style>
