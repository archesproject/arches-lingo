<script setup lang="ts">
import { nextTick, ref, useTemplateRef, watch } from "vue";
import { storeToRefs } from "pinia";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";
import { useConfirm } from "primevue/useconfirm";

import ConfirmDialog from "primevue/confirmdialog";

import ConceptSetList from "@/arches_lingo/components/concept-set-browser/components/ConceptSetList.vue";
import ConceptSetMemberList from "@/arches_lingo/components/concept-set-browser/components/ConceptSetMemberList.vue";

import {
    fetchConceptSetDetail,
    createConceptSet,
    deleteConceptSet,
    addToConceptSet,
    removeFromConceptSet,
} from "@/arches_lingo/api.ts";
import {
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    ERROR,
    SECONDARY,
    SUCCESS,
} from "@/arches_lingo/constants.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";
import { useConceptSetStore } from "@/arches_lingo/stores/useConceptSetStore.ts";

import type { ConceptSetDetail, ConceptSetItem } from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();
const toast = useToast();
const confirm = useConfirm();
const { isAnonymous } = storeToRefs(useUserStore());

// Distinct from the advanced search ConceptSets group, which can be mounted
// at the same time.
const DELETE_CONCEPT_SET_CONFIRM_GROUP = "delete-browser-concept-set";

const conceptSetStore = useConceptSetStore();
const { conceptSets } = storeToRefs(conceptSetStore);
const activeSetDetail = ref<ConceptSetDetail | null>(null);
const conceptSetList =
    useTemplateRef<InstanceType<typeof ConceptSetList>>("conceptSetList");
const conceptSetMemberList = useTemplateRef<
    InstanceType<typeof ConceptSetMemberList>
>("conceptSetMemberList");

async function loadConceptSets() {
    try {
        await conceptSetStore.loadConceptSets();
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
        await nextTick();
        conceptSetMemberList.value?.focusBackButton();
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to load concept set."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

async function handleBackToList() {
    const previousSetId = activeSetDetail.value?.id;
    activeSetDetail.value = null;
    await nextTick();
    if (previousSetId) {
        conceptSetList.value?.focusSet(previousSetId);
    }
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

function confirmDeleteSet(setItem: ConceptSetItem) {
    confirm.require({
        group: DELETE_CONCEPT_SET_CONFIRM_GROUP,
        header: $gettext("Delete concept set?"),
        message: $gettext(
            'The concept set "%{name}" will be deleted. The concepts in it are not affected. This cannot be undone.',
            { name: setItem.name },
            true,
        ),
        accept: () => handleDeleteSet(setItem),
        rejectProps: {
            label: $gettext("Cancel"),
            severity: SECONDARY,
            outlined: true,
        },
        acceptProps: {
            label: $gettext("Delete"),
            severity: DANGER,
        },
    });
}

async function handleDeleteSet(setItem: ConceptSetItem) {
    try {
        await deleteConceptSet(setItem.id);
        const deletedSetIndex = conceptSets.value.findIndex(
            (existingSet) => existingSet.id === setItem.id,
        );
        conceptSets.value = conceptSets.value.filter(
            (existingSet) => existingSet.id !== setItem.id,
        );
        const setToFocus =
            conceptSets.value[deletedSetIndex] ??
            conceptSets.value[deletedSetIndex - 1];
        await nextTick();
        if (setToFocus) {
            conceptSetList.value?.focusSet(setToFocus.id);
        } else {
            conceptSetList.value?.focusNewSetButton();
        }
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
            ref="conceptSetMemberList"
            :set-detail="activeSetDetail"
            @back="handleBackToList"
            @remove-members="handleRemoveMembers"
            @add-current-concept="handleAddCurrentConcept"
        />
        <ConceptSetList
            v-else
            ref="conceptSetList"
            :concept-sets="conceptSets"
            @select-set="handleSelectSet"
            @create-set="handleCreateSet"
            @delete-set="confirmDeleteSet"
        />
        <ConfirmDialog :group="DELETE_CONCEPT_SET_CONFIRM_GROUP" />
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
