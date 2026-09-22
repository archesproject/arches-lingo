<script setup lang="ts">
import { ref } from "vue";

import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Dialog from "primevue/dialog";
import RadioButton from "primevue/radiobutton";

import { DANGER } from "@/arches_lingo/constants.ts";

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

// A suggested pair has no direction, but a merge does: one concept keeps its
// values and the other is folded into it. Nothing sensible can be defaulted
// here, so the choice is made before the merge dialog opens.
const survivorId = ref<string>(conceptA.id);

function onConfirm() {
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
        :header="$gettext('Which concept should survive?')"
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
                    "The surviving concept keeps its values and can take any of the other's. The other is folded into it.",
                )
            }}
        </p>

        <div class="direction-options">
            <label
                v-for="concept in [conceptA, conceptB]"
                :key="concept.id"
                class="direction-option"
                :class="{ selected: survivorId === concept.id }"
                :for="`survivor-${concept.id}`"
            >
                <RadioButton
                    v-model="survivorId"
                    :input-id="`survivor-${concept.id}`"
                    :value="concept.id"
                />
                <span class="direction-option-body">
                    <span>{{ nameOf(concept) }}</span>
                    <span class="direction-option-scheme">
                        {{ concept.scheme_name }}
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
                    :disabled="isLoading"
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
