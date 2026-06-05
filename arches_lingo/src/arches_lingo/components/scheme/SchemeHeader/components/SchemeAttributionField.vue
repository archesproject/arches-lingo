<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import InputText from "primevue/inputtext";

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
    <div class="header-item">
        <span class="header-item-label">
            {{ $gettext("Attribution:") }}
        </span>

        <template v-if="isEditingAttribution">
            <div class="attribution-input-wrapper">
                <InputText
                    v-model="attributionDraft"
                    size="small"
                    :placeholder="$gettext('Attribution text')"
                />
            </div>
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
        </template>

        <template v-else>
            <span class="header-item-value">
                {{ schemeAttribution?.attribution || $gettext("None") }}
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
        </template>
    </div>
</template>

<style scoped>
.attribution-input-wrapper {
    flex: 0 1 auto;
    min-width: 0;
    overflow: hidden;
}

:deep(input) {
    field-sizing: content;
    max-width: 100%;
}
</style>
