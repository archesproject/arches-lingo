<script setup lang="ts">
import { ref } from "vue";

import { useGettext } from "vue3-gettext";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import RadioButton from "primevue/radiobutton";

import { INFO, SECONDARY } from "@/arches_lingo/constants.ts";

const { resourceName, resourceType, isLoading } = defineProps<{
    resourceId: string;
    resourceName: string | undefined;
    resourceType: "concept" | "scheme";
    isLoading?: boolean;
}>();

const emit = defineEmits<{
    confirm: [cascade: boolean];
    cancel: [];
}>();

const { $gettext } = useGettext();

const selectedCascade = ref(false);

function dialogHeader(): string {
    return $gettext("Reinstate");
}

function confirmationText(): string {
    return $gettext(
        'Are you sure you want to reinstate "%{name}"? It will return to Editing state.',
        { name: resourceName ?? "" },
    );
}

function childrenText(): string {
    if (resourceType === "scheme") {
        return $gettext(
            'Would you also like to reinstate the concepts within "%{name}"?',
            { name: resourceName ?? "" },
        );
    }
    return $gettext(
        'Would you also like to reinstate the child concepts within "%{name}"?',
        { name: resourceName ?? "" },
    );
}

function reinstateOnlyLabel(): string {
    if (resourceType === "scheme") {
        return $gettext("Reinstate this scheme only");
    }
    return $gettext("Reinstate this concept only");
}

function reinstateAllLabel(): string {
    if (resourceType === "scheme") {
        return $gettext("Reinstate this scheme and all its concepts");
    }
    return $gettext("Reinstate this concept and all its descendants");
}

function reinstateAllDesc(): string {
    if (resourceType === "scheme") {
        return $gettext(
            "All retired concepts within this scheme will be moved to Editing state.",
        );
    }
    return $gettext(
        "This concept and all its retired descendants will be moved to Editing state.",
    );
}

function onConfirm() {
    emit("confirm", selectedCascade.value);
}
</script>

<template>
    <Dialog
        :visible="true"
        :modal="true"
        :dismissable-mask="false"
        :header="dialogHeader()"
        :closable="!isLoading"
        class="reinstate-dialog"
        @update:visible="!isLoading && $emit('cancel')"
    >
        <div class="dialog-body">
            <div class="dialog-text">{{ confirmationText() }}</div>
            <div class="dialog-text">{{ childrenText() }}</div>

            <div class="strategy-options">
                <label
                    class="strategy-option"
                    :class="{ selected: !selectedCascade }"
                    for="cascade-false"
                >
                    <RadioButton
                        v-model="selectedCascade"
                        input-id="cascade-false"
                        :value="false"
                    />
                    <div class="strategy-label">
                        <span class="strategy-title">{{
                            reinstateOnlyLabel()
                        }}</span>
                    </div>
                </label>

                <label
                    class="strategy-option"
                    :class="{ selected: selectedCascade }"
                    for="cascade-true"
                >
                    <RadioButton
                        v-model="selectedCascade"
                        input-id="cascade-true"
                        :value="true"
                    />
                    <div class="strategy-label">
                        <span class="strategy-title">{{
                            reinstateAllLabel()
                        }}</span>
                        <span class="strategy-desc">{{
                            reinstateAllDesc()
                        }}</span>
                    </div>
                </label>
            </div>
        </div>

        <template #footer>
            <Button
                :label="$gettext('Cancel')"
                :severity="SECONDARY"
                :disabled="isLoading"
                :outlined="true"
                @click="$emit('cancel')"
            />
            <Button
                :label="$gettext('Reinstate')"
                :severity="INFO"
                :disabled="isLoading"
                :loading="isLoading"
                @click="onConfirm"
            />
        </template>
    </Dialog>
</template>

<style scoped>
.reinstate-dialog {
    width: 34rem;
}

.dialog-body {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.dialog-text {
    margin: 0;
    font-size: var(--p-lingo-font-size-normal);
}

.strategy-options {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.strategy-option {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.75rem;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.25rem;
    cursor: pointer;
    transition:
        border-color 0.15s,
        background-color 0.15s;
}

.strategy-option.selected {
    border-color: var(--p-primary-color);
    background-color: var(--p-highlight-background);
}

.strategy-label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 0;
}

.strategy-title {
    font-size: var(--p-lingo-font-size-normal);
    color: var(--p-text-color);
}

.strategy-desc {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
}
</style>
