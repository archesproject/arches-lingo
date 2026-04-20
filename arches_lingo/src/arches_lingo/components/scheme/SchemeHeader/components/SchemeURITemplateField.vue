<script setup lang="ts">
import { computed, ref } from "vue";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Popover from "primevue/popover";

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
const infoPopoverRef = ref();

const schemeURITemplateValue = computed(() => {
    const savedTemplate = props.schemeURITemplate?.url_template?.trim();
    if (savedTemplate) {
        return savedTemplate;
    }

    return props.defaultSchemeURITemplate;
});

function toggleInfoPopover(event: Event) {
    infoPopoverRef.value.toggle(event);
}

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
        <Button
            icon="pi pi-info-circle"
            variant="text"
            size="small"
            :rounded="true"
            class="info-button"
            :aria-label="$gettext('URI template information')"
            @click="toggleInfoPopover"
        />
        <Popover ref="infoPopoverRef">
            <div class="template-info">
                <p class="intro">
                    {{
                        $gettext(
                            "Placeholders are substituted with real values when the scheme is promoted to Active.",
                        )
                    }}
                </p>

                <div class="placeholder-entry">
                    <div class="placeholder-heading">
                        <code>&lt;scheme_identifier&gt;</code>
                        <span class="required-badge">{{
                            $gettext("Required")
                        }}</span>
                    </div>
                    <p>{{ $gettext("The scheme's identifier value.") }}</p>
                </div>

                <div class="placeholder-entry">
                    <div class="placeholder-heading">
                        <code>&lt;concept_counter&gt;</code>
                    </div>
                    <p>
                        {{
                            $gettext(
                                "A sequential number allocated to each concept.",
                            )
                        }}
                    </p>
                </div>

                <div class="placeholder-entry">
                    <div class="placeholder-heading">
                        <code>&lt;scheme_and_concept_counter&gt;</code>
                    </div>
                    <p>
                        {{
                            $gettext(
                                "A shared number sequence for both the scheme and its concepts. The scheme takes the counter start value; each concept receives the next value in the sequence.",
                            )
                        }}
                    </p>
                </div>

                <p class="examples-heading">{{ $gettext("Examples:") }}</p>
                <code class="template-example">
                    http://example.org/schemes/&lt;scheme_identifier&gt;/concepts/&lt;concept_counter&gt;
                </code>
                <code class="template-example">
                    http://example.org/&lt;scheme_identifier&gt;/&lt;scheme_and_concept_counter&gt;
                </code>
            </div>
        </Popover>

        <span class="header-item-label">
            {{ $gettext("URI template:") }}
        </span>

        <template v-if="isEditingSchemeURITemplate">
            <div class="uri-input-wrapper">
                <InputText
                    v-model="schemeURITemplateDraft"
                    size="small"
                    :placeholder="
                        $gettext(
                            'Placeholders: <scheme_identifier>, <concept_counter>, <scheme_and_concept_counter>',
                        )
                    "
                />
            </div>
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

<style scoped>
.header-item > .info-button {
    padding: 0;
    width: unset;
    height: auto;
    margin-inline-end: 0.25rem;
}

.uri-input-wrapper {
    flex: 0 1 auto;
    min-width: 0;
    overflow: hidden;
}

:deep(input) {
    field-sizing: content;
    max-width: 100%;
}

.template-info {
    max-width: 22rem;
    display: flex;
    flex-direction: column;
    gap: 0.625rem;
}

.intro,
.examples-heading {
    margin: 0;
    font-size: var(--p-lingo-font-size-smallnormal);
    line-height: 1.4;
}

.examples-heading {
    margin-top: 0.25rem;
}

.placeholder-entry {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}

.placeholder-heading {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.placeholder-entry p {
    margin: 0;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
    line-height: 1.4;
}

.required-badge {
    font-size: var(--p-lingo-font-size-small);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-red-500);
    border: 0.0625rem solid var(--p-red-300);
    border-radius: 0.25rem;
    padding: 0 0.25rem;
    white-space: nowrap;
}

.template-example {
    display: block;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
    word-break: break-all;
    padding: 0.25rem 0.5rem;
    background: var(--p-content-background);
    border-radius: 0.25rem;
}
</style>
