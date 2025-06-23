<script setup lang="ts">
import { computed, provide, ref } from "vue";

import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import { MAXIMIZE, MINIMIZE, CLOSE } from "@/arches_lingo/constants.ts";

const props = defineProps<{
    isEditorMaximized: boolean;
}>();

const { $gettext } = useGettext();

const emit = defineEmits([MAXIMIZE, MINIMIZE, CLOSE]);

const formKey = ref(0);
const componentEditorFormRef = ref();
provide("componentEditorFormRef", componentEditorFormRef);
provide("resetForm", resetForm);

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

function toggleSize() {
    if (props.isEditorMaximized) {
        emit(MINIMIZE);
    } else {
        emit(MAXIMIZE);
    }
}

function handleCancelClick() {
    const wasDirty = isFormDirty.value;
    // Store the dirty state for the reset handler to use
    componentEditorFormRef.value._wasDirty = wasDirty;
    componentEditorFormRef.value.onReset();
}

function resetForm() {
    const wasDirty = componentEditorFormRef.value?._wasDirty ?? false;
    if (wasDirty) {
        formKey.value += 1;
    } else {
        emit(CLOSE);
    }
    // Clean up the temporary flag
    if (componentEditorFormRef.value) {
        delete componentEditorFormRef.value._wasDirty;
    }
}
</script>

<template>
    <div class="container">
        <div class="header">
            <h2>{{ $gettext("Editor Tools") }}</h2>

            <div class="controls">
                <Button
                    :aria-label="$gettext('toggle editor size')"
                    rounded
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
                    rounded
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
                @click="componentEditorFormRef.onSubmit()"
            />
            <Button
                :label="$gettext('Cancel')"
                severity="danger"
                @click="handleCancelClick"
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

.controls button {
    margin: 0 0.125rem;
}

h2 {
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 0.125rem solid var(--p-menubar-border-color);
    background: var(--p-header-background);
    padding: 0 1rem;
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

.editor-content :deep(h3) {
    font-size: var(--p-lingo-font-size-medium);
    font-weight: var(--p-lingo-font-weight-normal);
}

.editor-content :deep(.p-formfield) {
    margin-bottom: 0.65rem;
}

.editor-content {
    overflow-y: auto;
    flex: 1;
    padding: 0 1rem 0 1rem;
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
}
</style>
