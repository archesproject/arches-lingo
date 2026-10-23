<script setup lang="ts">
import { computed, ref } from "vue";

import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Dialog from "primevue/dialog";
import Message from "primevue/message";
import RadioButton from "primevue/radiobutton";

import { MERGE_DIALOG_FRAME_PASS_THROUGH } from "@/arches_lingo/components/concept/ConceptMerge/constants.ts";
import { CANNOT_RECEIVE_SCHEME_LOCKED } from "@/arches_lingo/components/ConceptMatching/constants.ts";
import { useLocalizedLabel } from "@/arches_lingo/components/ConceptMatching/composables/useLocalizedLabel.ts";
import { DANGER, WARN } from "@/arches_lingo/constants.ts";

import type { MatchedConceptSummary } from "@/arches_lingo/types.ts";
import type { MergeDirection } from "@/arches_lingo/components/ConceptMatching/types.ts";

const DIALOG_PASS_THROUGH = {
    ...MERGE_DIALOG_FRAME_PASS_THROUGH,
    root: {
        style: {
            ...MERGE_DIALOG_FRAME_PASS_THROUGH.root.style,
            width: "34rem",
            maxWidth: "92vw",
        },
    },
    content: {
        style: { padding: "1.25rem", paddingBlockStart: "1rem" },
    },
};

const { conceptA, conceptB, isLoading } = defineProps<{
    conceptA: MatchedConceptSummary;
    conceptB: MatchedConceptSummary;
    isLoading: boolean;
}>();

const emit = defineEmits<{
    (event: "direction-chosen", payload: MergeDirection): void;
    (event: "cancel"): void;
}>();

const { $gettext } = useGettext();
const { labelOf } = useLocalizedLabel();

// A merge writes only to the survivor, so a published or locked concept can still be absorbed.
const survivorId = ref<string | null>(
    [conceptA, conceptB].find((concept) => concept.can_receive_data)?.id ??
        null,
);

const pairedConcepts = computed(() => [conceptA, conceptB]);

const canMergeEitherWay = computed(
    () => conceptA.can_receive_data || conceptB.can_receive_data,
);

const canContinue = computed(() => !isLoading && survivorId.value !== null);

function whyUnavailable(
    reason: MatchedConceptSummary["cannot_receive_reason"],
): string {
    if (reason === CANNOT_RECEIVE_SCHEME_LOCKED) {
        return $gettext("Its scheme is locked, so nothing can be added to it.");
    }
    return $gettext(
        "It is not in a state that accepts new values, so nothing can be added to it.",
    );
}

function onContinue(): void {
    if (!survivorId.value) return;
    const survivorIsFirst = survivorId.value === conceptA.id;
    emit("direction-chosen", {
        survivor: survivorIsFirst ? conceptA : conceptB,
        absorbed: survivorIsFirst ? conceptB : conceptA,
    });
}

function onVisibilityChange(): void {
    if (!isLoading) emit("cancel");
}
</script>

<template>
    <Dialog
        class="direction-dialog"
        :visible="true"
        :modal="true"
        :header="$gettext('Which concept should take the other\'s values?')"
        :closable="!isLoading"
        :pt="DIALOG_PASS_THROUGH"
        @update:visible="onVisibilityChange"
    >
        <div class="direction-body">
            <p class="direction-intro">
                {{
                    $gettext(
                        "The concept you choose keeps everything it has and takes the values you select from the other. Those values are copied, so nothing is removed from the other concept — retiring it is a separate choice later in the merge, and only offered within a single scheme.",
                    )
                }}
            </p>

            <Message
                v-if="!canMergeEitherWay"
                class="direction-message"
                :severity="WARN"
                :closable="false"
            >
                <span>{{
                    $gettext(
                        "Neither concept can be added to, so this pair cannot be merged.",
                    )
                }}</span>
            </Message>

            <div class="direction-options">
                <label
                    v-for="concept in pairedConcepts"
                    :key="concept.id"
                    class="direction-option"
                    :class="{
                        selected: survivorId === concept.id,
                        unavailable: !concept.can_receive_data,
                    }"
                    :for="`survivor-${concept.id}`"
                >
                    <RadioButton
                        v-model="survivorId"
                        name="merge-survivor"
                        :input-id="`survivor-${concept.id}`"
                        :value="concept.id"
                        :disabled="!concept.can_receive_data"
                    />
                    <span class="direction-option-body">
                        <span>{{ labelOf(concept) }}</span>
                        <span class="direction-option-scheme">
                            {{ concept.scheme_name }}
                        </span>
                        <span
                            v-if="!concept.can_receive_data"
                            class="direction-option-unavailable"
                        >
                            {{ whyUnavailable(concept.cannot_receive_reason) }}
                        </span>
                    </span>
                </label>
            </div>
        </div>

        <template #footer>
            <div class="direction-footer">
                <Button
                    class="direction-button"
                    icon="pi pi-times"
                    :label="$gettext('Cancel')"
                    :severity="DANGER"
                    :disabled="isLoading"
                    @click="emit('cancel')"
                />
                <Button
                    class="direction-button"
                    icon="pi pi-arrow-right"
                    icon-pos="right"
                    :label="$gettext('Continue')"
                    :disabled="!canContinue"
                    :loading="isLoading"
                    @click="onContinue"
                />
            </div>
        </template>
    </Dialog>
</template>

<style scoped>
.direction-body {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.direction-body .direction-intro {
    margin: 0;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
}

.direction-body .direction-message {
    font-size: var(--p-lingo-font-size-smallnormal);
}

.direction-body .direction-options {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.direction-body .direction-options .direction-option {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.625rem;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.125rem;
    cursor: pointer;
}

.direction-body .direction-options .direction-option.selected {
    border-color: var(--p-primary-color);
    background-color: var(--p-highlight-background);
}

.direction-body .direction-options .direction-option.unavailable {
    cursor: not-allowed;
    opacity: 0.65;
}

.direction-body .direction-option .direction-option-body {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    min-width: 0;
}

.direction-body .direction-option-body .direction-option-scheme,
.direction-body .direction-option-body .direction-option-unavailable {
    font-size: var(--p-lingo-font-size-xxsmall);
    color: var(--p-text-muted-color);
}

.direction-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
}

.direction-footer .direction-button {
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
}
</style>
