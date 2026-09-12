<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Textarea from "primevue/textarea";

import { upsertSchemeAttribution } from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";

type SchemeAttribution = {
    scheme_resource_instance_id: string;
    attribution: string;
};

const props = defineProps<{
    resourceInstanceId: string | undefined;
    canEditResourceInstances: boolean;
    schemeAttribution: SchemeAttribution | undefined;
}>();

const emit = defineEmits<{
    (
        eventName: "update",
        payload: { schemeAttribution: SchemeAttribution | undefined },
    ): void;
}>();

const toast = useToast();
const { $gettext } = useGettext();

const isEditingAttribution = ref(false);
const attributionDraft = ref("");
const isSavingAttribution = ref(false);

function editAttribution() {
    attributionDraft.value = props.schemeAttribution?.attribution ?? "";
    isEditingAttribution.value = true;
}

function cancelEditingAttribution() {
    attributionDraft.value = "";
    isEditingAttribution.value = false;
}

async function saveAttribution() {
    if (!props.resourceInstanceId) {
        return;
    }

    isSavingAttribution.value = true;

    try {
        const updatedAttribution = await upsertSchemeAttribution(
            props.resourceInstanceId,
            attributionDraft.value,
        );

        emit("update", { schemeAttribution: updatedAttribution });

        cancelEditingAttribution();
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to save attribution"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isSavingAttribution.value = false;
    }
}
</script>

<template>
    <div class="header-item attribution-header-item">
        <span class="header-item-label">
            {{ $gettext("Attribution:") }}
        </span>

        <template v-if="isEditingAttribution">
            <div class="attribution-input-wrapper">
                <Textarea
                    v-model="attributionDraft"
                    :rows="4"
                    :placeholder="
                        $gettext('Enter attribution information here...')
                    "
                />
                <div class="attribution-edit-controls">
                    <Button
                        icon="pi pi-check"
                        variant="text"
                        severity="success"
                        size="small"
                        :rounded="true"
                        :aria-label="$gettext('Save attribution')"
                        :loading="isSavingAttribution"
                        @click="saveAttribution"
                    />
                    <Button
                        icon="pi pi-times"
                        variant="text"
                        severity="danger"
                        size="small"
                        :rounded="true"
                        :aria-label="$gettext('Cancel')"
                        :disabled="isSavingAttribution"
                        @click="cancelEditingAttribution"
                    />
                </div>
            </div>
        </template>

        <template v-else>
            <span
                v-if="!schemeAttribution?.attribution"
                class="header-item-value"
            >
                {{ $gettext("None") }}
            </span>
            <Button
                v-if="canEditResourceInstances"
                icon="pi pi-pencil"
                variant="text"
                size="small"
                :rounded="true"
                :aria-label="$gettext('Edit attribution')"
                @click="editAttribution"
            />
            <div
                v-if="schemeAttribution?.attribution"
                class="attribution-value"
            >
                {{ schemeAttribution.attribution }}
            </div>
        </template>
    </div>
</template>

<style scoped>
.attribution-header-item {
    width: 100%;
    flex-wrap: wrap;
    align-items: center;
}

.attribution-value {
    flex-basis: 100%;
    width: 100%;
    white-space: pre-wrap;
    word-break: break-word;
    overflow-y: auto;
    max-height: 9rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-primary-500);
    background: var(--p-content-background);
    border: 1px solid var(--p-content-border-color);
    border-radius: var(--p-border-radius-sm);
    padding: 0.375rem 0.5rem;
    box-sizing: border-box;
}

.attribution-input-wrapper {
    display: flex;
    flex-direction: row;
    flex-basis: 100%;
    min-width: 0;
}

.attribution-input-wrapper :deep(textarea) {
    width: 100%;
}

.attribution-edit-controls {
    display: flex;
    flex-direction: column;
}
</style>
