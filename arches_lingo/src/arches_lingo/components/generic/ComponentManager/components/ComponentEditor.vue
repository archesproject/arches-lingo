<script setup lang="ts">
import { computed, nextTick, provide, ref, useTemplateRef, watch } from "vue";

import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import { MAXIMIZE, MINIMIZE, CLOSE } from "@/arches_lingo/constants.ts";

const props = defineProps<{
    isEditorMaximized: boolean;
    isEditorLoading: boolean;
}>();

const { $gettext } = useGettext();

const emit = defineEmits([MAXIMIZE, MINIMIZE, CLOSE]);

const toggleSizeButton = useTemplateRef("toggleSizeButton");

const formKey = ref(0);
const componentEditorFormRef = ref();
provide("componentEditorFormRef", componentEditorFormRef);

const isFormDirty = computed(() => {
    if (componentEditorFormRef.value) {
        const formFields = Object.keys(componentEditorFormRef.value.states);
        const states = formFields.map((field) => {
            return componentEditorFormRef.value.states[field].dirty;
        });
        return states.some((state) => state === true);
    }
    return false;
});

// onMounted(() => {
//     nextTick(() => {
//         // @ts-expect-error This is an error in PrimeVue types
//         toggleSizeButton.value!.$el.focus();
//     });
// });

watch(
    () => props.isEditorLoading,
    (isLoaded) => {
        if (isLoaded === false) {
            nextTick(() => {
                console.log("loading finished, shift focus");
                const editorContent = document.querySelector(
                    ".editor-content",
                ) as HTMLElement;
                const firstTabbableElement = editorContent.querySelector(
                    'button, input, select, textarea, [tabindex]:not([tabindex="-1"])',
                ) as HTMLElement;
                if (firstTabbableElement) {
                    firstTabbableElement.focus();
                    console.log("shifted focus to editor content");
                } else {
                    // @ts-expect-error This is an error in PrimeVue types
                    toggleSizeButton.value!.$el.focus();
                    console.log("shifted focus to toggle size button");
                }
            });
        }
    },
);

function toggleSize() {
    if (props.isEditorMaximized) {
        emit(MINIMIZE);
    } else {
        emit(MAXIMIZE);
    }
}

function onCancel() {
    if (isFormDirty.value) {
        formKey.value += 1;
    } else {
        emit(CLOSE);
    }
}
</script>

<template>
    <div class="container">
        <div class="header">
            <h2>{{ $gettext("Editor Tools") }}</h2>

            <div class="controls">
                <Button
                    ref="toggleSizeButton"
                    class="panel-control-button"
                    :aria-label="$gettext('toggle editor size')"
                    @click="toggleSize"
                >
                    <i
                        :class="{
                            pi: true,
                            'pi-window-maximize': props.isEditorMaximized,
                            'pi-window-minimize': !props.isEditorMaximized,
                        }"
                        aria-hidden="true"
                    />
                </Button>
                <Button
                    :aria-label="$gettext('close editor')"
                    class="panel-control-button"
                    @click="$emit(CLOSE)"
                >
                    <i
                        class="pi pi-times"
                        aria-hidden="true"
                    />
                </Button>
            </div>
        </div>

        <div class="editor-content">
            <slot :key="formKey" />
        </div>

        <div class="footer">
            <Button
                :label="$gettext('Save Changes')"
                severity="success"
                :disabled="!isFormDirty"
                @click="componentEditorFormRef.submit()"
            />
            <Button
                :label="$gettext('Cancel')"
                severity="danger"
                @click="onCancel"
            />
        </div>
    </div>
</template>

<style scoped>
.container {
    display: flex;
    flex-direction: column;
    height: 100%;
}

.panel-control-button {
    border-radius: 50%;
    height: 2.25rem;
    width: 2.25rem;
    background: var(--p-primary-contrast-color);
    border: 0.0625rem solid var(--p-header-button-border);
    color: var(--p-editor-form-color);
}

.controls button {
    margin: 0 0.125rem;
}

h2 {
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
    margin: 0.75rem 0rem;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    background: var(--p-header-toolbar-background);
    padding: 0 1rem;
    padding-bottom: 0.1rem;
}

.header > Button {
    margin: 0 0.125rem;
}

.editor-form {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
}

.editor-content {
    overflow-y: auto;
    flex: 1;
    padding: 0;
    background: var(--p-editor-form-background);
}

.editor-content :deep(.widget-container) {
    display: flex;
    gap: 0.25rem;
    padding: 0.5rem 0 0.25rem 0;
    color: var(--p-header-item-label);
}

.editor-content :deep(.column) {
    flex-direction: column;
}

.editor-content :deep(.form-header) {
    padding-top: 0;
    padding-bottom: 1rem;
    background: var(--p-header-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    min-height: 5.4rem;
}

.editor-content :deep(h3) {
    font-size: var(--p-lingo-font-size-medium);
    font-weight: var(--p-lingo-font-weight-normal);
}

.editor-content :deep(.form-header h3) {
    margin: 0;
    padding: 0.5rem 1rem 0 1rem;
    font-size: 1.125rem;
}

.editor-content :deep(.form-container) {
    padding: 0.5rem 1rem;
    background: var(--p-editor-form-background);
}

.editor-content :deep(.form-description) {
    padding: 0.125rem 1rem;
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-header-item-label);
    margin-inline-end: 0.25rem;
}

.editor-content :deep(.p-formfield) {
    margin-bottom: 0.65rem;
}

.editor-content :deep(.p-inputtext),
.editor-content :deep(.p-multiselect),
.editor-content :deep(.p-textarea),
.editor-content :deep(.p-treeselect),
.editor-content :deep(.p-select) {
    border-radius: 0.125rem;
}

:deep(.p-inputtext) {
    font-size: 0.875rem !important;
}

:deep(.p-treeselect-label) {
    font-size: 0.875rem !important;
}

.footer {
    background: var(--p-header-background);
    border-top: 0.125rem solid var(--p-menubar-border-color);
    display: flex;
    padding: 1rem;
}

.footer > Button {
    margin: 0 0.5rem;
    flex: 1;
    border-radius: 0.125rem;
}
</style>
