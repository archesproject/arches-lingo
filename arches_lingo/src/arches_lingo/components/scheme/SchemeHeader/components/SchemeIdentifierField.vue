<script setup lang="ts">
import { computed, nextTick, ref, useId } from "vue";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import InputText from "primevue/inputtext";

import { upsertSchemeIdentifier } from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";
import { focusFirstElementById } from "@/arches_lingo/utils.ts";

const props = defineProps<{
    resourceInstanceId: string | undefined;
    identifierValue: string | undefined;
    resourceIdentifierId: number | undefined;
    canEditResourceInstances: boolean;
}>();

const identifierLabelId = useId();
const identifierInputId = useId();
const identifierEditButtonId = useId();

const emit = defineEmits<{
    (
        eventName: "update",
        payload: {
            identifierValue: string | undefined;
            resourceIdentifierId: number | undefined;
        },
    ): void;
}>();

const toast = useToast();
const { $gettext } = useGettext();

const isEditingIdentifier = ref(false);
const identifierDraft = ref("");
const isSavingIdentifier = ref(false);

const shouldShowIdentifierEditButton = computed(() => {
    return props.canEditResourceInstances;
});

async function editIdentifier() {
    identifierDraft.value = props.identifierValue || "";
    isEditingIdentifier.value = true;
    await nextTick();
    focusFirstElementById(identifierInputId);
}

async function cancelEditingIdentifier() {
    identifierDraft.value = "";
    isEditingIdentifier.value = false;
    await nextTick();
    focusFirstElementById(identifierEditButtonId, identifierLabelId);
}

async function saveIdentifier() {
    if (!props.resourceInstanceId) {
        return;
    }

    isSavingIdentifier.value = true;

    try {
        const identifierData = await upsertSchemeIdentifier(
            props.resourceInstanceId,
            identifierDraft.value,
        );

        emit("update", {
            identifierValue: identifierData.identifier,
            resourceIdentifierId: identifierData.id,
        });

        cancelEditingIdentifier();
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to save identifier"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isSavingIdentifier.value = false;
    }
}
</script>

<template>
    <div class="header-item identifier-item">
        <span
            :id="identifierLabelId"
            class="header-item-label"
        >
            {{ $gettext("Identifier:") }}
        </span>

        <template v-if="isEditingIdentifier">
            <InputText
                :id="identifierInputId"
                v-model="identifierDraft"
                :aria-labelledby="identifierLabelId"
                size="small"
            />
            <Button
                icon="pi pi-check"
                variant="text"
                severity="success"
                size="small"
                :rounded="true"
                :aria-label="$gettext('Save Identifier')"
                :loading="isSavingIdentifier"
                @click="saveIdentifier"
            />
            <Button
                icon="pi pi-times"
                variant="text"
                severity="danger"
                size="small"
                :rounded="true"
                :aria-label="$gettext('Cancel')"
                :disabled="isSavingIdentifier"
                @click="cancelEditingIdentifier"
            />
        </template>

        <template v-else>
            <span class="header-item-value identifier-value">
                {{ identifierValue || $gettext("None") }}
            </span>
            <Button
                v-if="shouldShowIdentifierEditButton"
                :id="identifierEditButtonId"
                icon="pi pi-pencil"
                variant="text"
                size="small"
                class="identifier-edit-button"
                :rounded="true"
                :aria-label="$gettext('Edit Identifier')"
                @click="editIdentifier"
            />
        </template>
    </div>
</template>
