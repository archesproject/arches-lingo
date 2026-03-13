<script setup lang="ts">
import { computed, ref } from "vue";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import InputText from "primevue/inputtext";

import { upsertSchemeURITemplate } from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";

type SchemeURITemplate = {
    scheme_resource_instance_id: string;
    url_template: string;
};

const props = defineProps<{
    resourceInstanceId: string | undefined;
    canEditResourceInstances: boolean;
    schemeURITemplate: SchemeURITemplate | undefined;
    defaultSchemeURITemplate: string | undefined;
}>();

const emit = defineEmits<{
    (
        eventName: "update",
        payload: { schemeURITemplate: SchemeURITemplate | undefined },
    ): void;
}>();

const toast = useToast();
const { $gettext } = useGettext();

const isEditingSchemeURITemplate = ref(false);
const schemeURITemplateDraft = ref("");
const isSavingSchemeURITemplate = ref(false);

const schemeURITemplateValue = computed(() => {
    const savedTemplate = props.schemeURITemplate?.url_template?.trim();
    if (savedTemplate) {
        return savedTemplate;
    }

    return props.defaultSchemeURITemplate;
});

function editSchemeURITemplate() {
    schemeURITemplateDraft.value = schemeURITemplateValue.value || "";
    isEditingSchemeURITemplate.value = true;
}

function cancelEditingSchemeURITemplate() {
    schemeURITemplateDraft.value = "";
    isEditingSchemeURITemplate.value = false;
}

async function saveSchemeURITemplate() {
    if (!props.resourceInstanceId) {
        return;
    }

    isSavingSchemeURITemplate.value = true;

    try {
        const updatedTemplate = await upsertSchemeURITemplate(
            props.resourceInstanceId,
            schemeURITemplateDraft.value,
        );

        emit("update", { schemeURITemplate: updatedTemplate });

        cancelEditingSchemeURITemplate();
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to save scheme URL template"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isSavingSchemeURITemplate.value = false;
    }
}
</script>

<template>
    <div class="header-item">
        <span class="header-item-label">
            {{ $gettext("URI template:") }}
        </span>

        <template v-if="isEditingSchemeURITemplate">
            <InputText
                v-model="schemeURITemplateDraft"
                size="small"
                :placeholder="
                    $gettext(
                        'Placeholders: <scheme_identifier>, <concept_identifier>',
                    )
                "
            />
            <Button
                icon="pi pi-check"
                variant="text"
                severity="success"
                size="small"
                :rounded="true"
                :aria-label="$gettext('Save URL template')"
                :loading="isSavingSchemeURITemplate"
                @click="saveSchemeURITemplate"
            />
            <Button
                icon="pi pi-times"
                variant="text"
                severity="danger"
                size="small"
                :rounded="true"
                :aria-label="$gettext('Cancel')"
                :disabled="isSavingSchemeURITemplate"
                @click="cancelEditingSchemeURITemplate"
            />
        </template>

        <template v-else>
            <span class="header-item-value">
                {{ schemeURITemplateValue || $gettext("None") }}
            </span>
            <Button
                v-if="canEditResourceInstances"
                icon="pi pi-pencil"
                variant="text"
                size="small"
                :rounded="true"
                :aria-label="$gettext('Edit URL template')"
                @click="editSchemeURITemplate"
            />
        </template>
    </div>
</template>
