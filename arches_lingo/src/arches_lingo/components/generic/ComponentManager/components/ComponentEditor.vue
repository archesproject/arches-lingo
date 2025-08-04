<script setup lang="ts">
import {
    computed,
    nextTick,
    onMounted,
    provide,
    ref,
    useTemplateRef,
} from "vue";

import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import { MAXIMIZE, MINIMIZE, CLOSE } from "@/arches_lingo/constants.ts";

const props = defineProps<{
    isEditorMaximized: boolean;
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

onMounted(() => {
    nextTick(() => {
        // @ts-expect-error This is an error in PrimeVue types
        toggleSizeButton.value!.$el.focus();
    });
});

function toggleSize() {
    if (props.isEditorMaximized) {
        emit(MINIMIZE);
    } else {
        emit(MAXIMIZE);
    }
}

function onCancel() {
    if (isFormDirty.value) {
        componentEditorFormRef.value.onReset();
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

.controls button {
    margin: 0 0.125rem;
}

h2 {
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
    margin: .75rem 0rem;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    background: var(--p-header-toolbar-background);
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
    padding: 0;
    background: var(--p-editor-form-background);
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
