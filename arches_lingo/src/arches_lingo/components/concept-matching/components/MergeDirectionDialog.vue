<script setup lang="ts">
import { computed, ref } from "vue";

import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Dialog from "primevue/dialog";
import Message from "primevue/message";
import RadioButton from "primevue/radiobutton";

import { DANGER, WARN } from "@/arches_lingo/constants.ts";

import type { MatchedConceptSummary } from "@/arches_lingo/types.ts";

const { conceptA, conceptB, nameOf, isLoading } = defineProps<{
    conceptA: MatchedConceptSummary;
    conceptB: MatchedConceptSummary;
    nameOf: (concept: MatchedConceptSummary) => string;
    isLoading: boolean;
}>();

const emit = defineEmits<{
    (event: "confirm", survivorId: string, absorbedId: string): void;
    (event: "cancel"): void;
}>();

const { $gettext } = useGettext();

// A suggested pair has no direction, but a merge does: the values are copied
// one way, so which concept receives them is chosen before the merge dialog
// opens.
//
// A merge only writes to the concept receiving the values, which is why a
// published or locked concept can still be the one merged from. It cannot be
// the one merged into, so it is not offered as one.
const survivorId = ref<string | null>(
    [conceptA, conceptB].find((concept) => concept.can_receive_data)?.id ??
        null,
);

const canMergeEitherWay = computed(function () {
    return conceptA.can_receive_data || conceptB.can_receive_data;
});

function whyUnavailable(reason: string | null) {
    if (reason === "scheme_locked") {
        return $gettext("Its scheme is locked, so nothing can be added to it.");
    }
    return $gettext(
        "It is not in a state that accepts new values, so nothing can be added to it.",
    );
}

function onConfirm() {
    if (!survivorId.value) return;
    emit(
        "confirm",
        survivorId.value,
        survivorId.value === conceptA.id ? conceptB.id : conceptA.id,
    );
}
</script>

<template>
    <Dialog
        :visible="true"
        :modal="true"
        :header="$gettext('Which concept should take the other\'s values?')"
        class="direction-dialog"
        :closable="!isLoading"
        :pt="{
            root: {
                style: {
                    fontFamily: 'var(--p-lingo-font-family)',
                    fontSize: 'var(--p-lingo-font-size-small)',
                    border: '0.125rem solid var(--p-dialog-color)',
                    borderRadius: '0.25rem',
                    width: '34rem',
                    maxWidth: '92vw',
                },
            },
            header: {
                style: {
                    background: 'var(--p-navigation-header-color)',
                    color: 'var(--p-dialog-header-text-color)',
                    borderRadius: '0',
                    paddingBlock: '1.25rem',
                    paddingInline: '1.5rem',
                },
            },
            title: {
                style: {
                    fontSize: 'var(--p-lingo-font-size-large)',
                    fontWeight: 'var(--p-lingo-font-weight-normal)',
                    lineHeight: '1.2',
                },
            },
            content: { style: { padding: '1.25rem', paddingTop: '1rem' } },
        }"
        @update:visible="!isLoading && emit('cancel')"
    >
        <p class="direction-intro">
            {{
                $gettext(
                    "The concept you choose keeps everything it has and takes the values you select from the other. Those values are copied, so nothing is removed from the other concept \u2014 retiring it is a separate choice later in the merge, and only offered within a single scheme.",
                )
            }}
        </p>

        <Message
            v-if="!canMergeEitherWay"
            :severity="WARN"
            :closable="false"
            class="direction-message"
        >
            {{
                $gettext(
                    "Neither concept can be added to, so this pair cannot be merged.",
                )
            }}
        </Message>

        <div class="direction-options">
            <label
                v-for="concept in [conceptA, conceptB]"
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
                    :input-id="`survivor-${concept.id}`"
                    :value="concept.id"
                    :disabled="!concept.can_receive_data"
                />
                <span class="direction-option-body">
                    <span>{{ nameOf(concept) }}</span>
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

        <template #footer>
            <div class="direction-footer">
                <Button
                    icon="pi pi-times"
                    :label="$gettext('Cancel')"
                    :severity="DANGER"
                    :disabled="isLoading"
                    class="direction-button"
                    @click="emit('cancel')"
                />
                <Button
                    icon="pi pi-arrow-right"
                    icon-pos="right"
                    :label="$gettext('Continue')"
                    :disabled="isLoading || !survivorId"
                    :loading="isLoading"
                    class="direction-button"
                    @click="onConfirm"
                />
            </div>
        </template>
    </Dialog>
</template>

<style scoped>
.direction-intro {
    margin: 0 0 0.75rem 0;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
}

.direction-options {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.direction-option {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.625rem;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.125rem;
    cursor: pointer;
}

.direction-option.selected {
    border-color: var(--p-primary-color);
    background-color: var(--p-highlight-background);
}

.direction-option.unavailable {
    cursor: not-allowed;
    opacity: 0.65;
}

.direction-option-unavailable {
    font-size: var(--p-lingo-font-size-xxsmall);
    color: var(--p-inputtext-placeholder-color);
}

.direction-message {
    margin-bottom: 0.75rem;
    font-size: var(--p-lingo-font-size-smallnormal);
}

.direction-option-body {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    min-width: 0;
}

.direction-option-scheme {
    font-size: var(--p-lingo-font-size-xxsmall);
    color: var(--p-neutral-400);
}

.direction-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
}

.direction-button {
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
}

:deep(.p-dialog) {
    border-radius: 0.125rem;
}
</style>
