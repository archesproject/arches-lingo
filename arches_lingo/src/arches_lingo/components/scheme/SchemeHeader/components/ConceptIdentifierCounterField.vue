<script setup lang="ts">
import { computed, ref } from "vue";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import InputText from "primevue/inputtext";

import { createConceptIdentifierCounter } from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";

type ConceptIdentifierCounter = {
    scheme_resource_instance_id: string;
    start_number: number;
    next_number: number;
};

const props = defineProps<{
    resourceInstanceId: string | undefined;
    canEditResourceInstances: boolean;
    conceptIdentifierCounter: ConceptIdentifierCounter | undefined;
}>();

const emit = defineEmits<{
    (
        eventName: "update",
        payload: {
            conceptIdentifierCounter: ConceptIdentifierCounter | undefined;
        },
    ): void;
}>();

const toast = useToast();
const { $gettext } = useGettext();

const isEditingConceptIdentifierCounter = ref(false);
const conceptIdentifierCounterStartNumberDraft = ref("1");
const isSavingConceptIdentifierCounter = ref(false);

const shouldShowConceptIdentifierCounterEditButton = computed(() => {
    if (!props.canEditResourceInstances) {
        return false;
    }

    if (!props.conceptIdentifierCounter) {
        return true;
    }

    return (
        props.conceptIdentifierCounter.start_number ===
        props.conceptIdentifierCounter.next_number
    );
});

function editConceptIdentifierCounter() {
    if (!props.conceptIdentifierCounter) {
        conceptIdentifierCounterStartNumberDraft.value = "1";
    } else {
        conceptIdentifierCounterStartNumberDraft.value = String(
            props.conceptIdentifierCounter.start_number,
        );
    }

    isEditingConceptIdentifierCounter.value = true;
}

function cancelEditingConceptIdentifierCounter() {
    conceptIdentifierCounterStartNumberDraft.value = "1";
    isEditingConceptIdentifierCounter.value = false;
}

async function saveConceptIdentifierCounter() {
    if (!props.resourceInstanceId) {
        return;
    }

    isSavingConceptIdentifierCounter.value = true;

    try {
        const updatedCounter = await createConceptIdentifierCounter(
            props.resourceInstanceId,
            Number(conceptIdentifierCounterStartNumberDraft.value),
        );

        emit("update", { conceptIdentifierCounter: updatedCounter });

        cancelEditingConceptIdentifierCounter();
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to save concept identifier counter"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isSavingConceptIdentifierCounter.value = false;
    }
}
</script>

<template>
    <div class="header-item">
        <span class="header-item-label">
            {{ $gettext("Concept counter:") }}
        </span>

        <template v-if="isEditingConceptIdentifierCounter">
            <InputText
                v-model="conceptIdentifierCounterStartNumberDraft"
                size="small"
            />
            <Button
                icon="pi pi-check"
                variant="text"
                severity="success"
                size="small"
                :rounded="true"
                :aria-label="$gettext('Save concept identifier counter')"
                :loading="isSavingConceptIdentifierCounter"
                @click="saveConceptIdentifierCounter"
            />
            <Button
                icon="pi pi-times"
                variant="text"
                severity="danger"
                size="small"
                :rounded="true"
                :aria-label="$gettext('Cancel')"
                :disabled="isSavingConceptIdentifierCounter"
                @click="cancelEditingConceptIdentifierCounter"
            />
        </template>

        <template v-else>
            <span class="header-item-value">
                {{ conceptIdentifierCounter?.start_number ?? $gettext("None") }}
            </span>
            <Button
                v-if="shouldShowConceptIdentifierCounterEditButton"
                icon="pi pi-pencil"
                variant="text"
                size="small"
                :rounded="true"
                :aria-label="$gettext('Edit concept identifier counter')"
                @click="editConceptIdentifierCounter"
            />
        </template>
    </div>
</template>
