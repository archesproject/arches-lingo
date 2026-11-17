<script setup lang="ts">
import { computed, nextTick, ref, useId } from "vue";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import InputNumber from "primevue/inputnumber";

import type { InputNumberInputEvent } from "primevue/inputnumber";

import DisabledReasonButton from "@/arches_lingo/components/generic/DisabledReasonButton.vue";

import { createConceptIdentifierCounter } from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";
import { focusFirstElementById } from "@/arches_lingo/utils.ts";

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

const conceptIdentifierCounterLabelId = useId();
const conceptIdentifierCounterInputId = useId();
const conceptIdentifierCounterEditButtonId = useId();

const isEditingConceptIdentifierCounter = ref(false);
const conceptIdentifierCounterStartNumberDraft = ref<number | null>(1);
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

const isStartNumberDraftEmpty = computed(
    () => conceptIdentifierCounterStartNumberDraft.value === null,
);

function onStartNumberInput(event: InputNumberInputEvent) {
    if (typeof event.value === "number") {
        conceptIdentifierCounterStartNumberDraft.value = event.value;
        return;
    }
    conceptIdentifierCounterStartNumberDraft.value = null;
}

async function editConceptIdentifierCounter() {
    if (!props.conceptIdentifierCounter) {
        conceptIdentifierCounterStartNumberDraft.value = 1;
    } else {
        conceptIdentifierCounterStartNumberDraft.value =
            props.conceptIdentifierCounter.start_number;
    }

    isEditingConceptIdentifierCounter.value = true;
    await nextTick();
    focusFirstElementById(conceptIdentifierCounterInputId);
}

async function cancelEditingConceptIdentifierCounter() {
    conceptIdentifierCounterStartNumberDraft.value = 1;
    isEditingConceptIdentifierCounter.value = false;
    await nextTick();
    focusFirstElementById(
        conceptIdentifierCounterEditButtonId,
        conceptIdentifierCounterLabelId,
    );
}

async function saveConceptIdentifierCounter() {
    const startNumber = conceptIdentifierCounterStartNumberDraft.value;
    if (!props.resourceInstanceId || startNumber === null) {
        return;
    }

    isSavingConceptIdentifierCounter.value = true;

    try {
        const updatedCounter = await createConceptIdentifierCounter(
            props.resourceInstanceId,
            startNumber,
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
        <span
            :id="conceptIdentifierCounterLabelId"
            class="header-item-label"
        >
            {{ $gettext("Concept counter:") }}
        </span>

        <template v-if="isEditingConceptIdentifierCounter">
            <InputNumber
                v-model="conceptIdentifierCounterStartNumberDraft"
                :input-id="conceptIdentifierCounterInputId"
                :aria-labelledby="conceptIdentifierCounterLabelId"
                :min="1"
                :use-grouping="false"
                size="small"
                @input="onStartNumberInput"
            />
            <DisabledReasonButton
                icon="pi pi-check"
                variant="text"
                severity="success"
                size="small"
                :rounded="true"
                :aria-label="$gettext('Save concept identifier counter')"
                :loading="isSavingConceptIdentifierCounter"
                :is-disabled="isStartNumberDraftEmpty"
                :disabled-reason="$gettext('Enter a valid start number')"
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
                :id="conceptIdentifierCounterEditButtonId"
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
