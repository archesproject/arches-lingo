<script setup lang="ts">
import { provide, ref } from "vue";

import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import { MAXIMIZE, MINIMIZE, CLOSE } from "@/arches_lingo/constants.ts";

const props = defineProps<{
    isEditorMaximized: boolean;
}>();

const { $gettext } = useGettext();

const emit = defineEmits([MAXIMIZE, MINIMIZE, CLOSE]);

const formKey = ref(0);
const schemeEditorFormRef = ref();
provide("schemeEditorFormRef", schemeEditorFormRef);

function toggleSize() {
    if (props.isEditorMaximized) {
        emit(MINIMIZE);
    } else {
        emit(MAXIMIZE);
    }
}

function resetForm() {
    formKey.value += 1;
}
</script>

<template>
    <div class="container">
        <div class="header">
            <h2>{{ $gettext("Editor Tools") }}</h2>

            <div>
                <Button
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

        <div>
            <Button
                :label="$gettext('Save Changes')"
                severity="success"
                @click="schemeEditorFormRef.onSubmit()"
            />
            <Button
                :label="$gettext('Cancel')"
                severity="danger"
                @click="resetForm"
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

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.editor-form {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
}

.editor-content {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
}
</style>
