<script setup lang="ts">
import { computed, ref } from "vue";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import InputFile from "primevue/fileupload";
import RadioButton from "primevue/radiobutton";
import ProgressSpinner from "primevue/progressspinner";

import { importThesaurus } from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";

const { $gettext } = useGettext();
const toast = useToast();

const emit = defineEmits<{
    (e: "imported"): void;
}>();

const visible = ref(true);
const loading = ref(false);
const file = ref<File | null>(null);
const overwriteOption = ref("overwrite");

const overwriteOptions = ref([
    {
        label: $gettext("Ignore"),
        value: "ignore",
        tooltip: $gettext("Do nothing if the Scheme or Concept already exists"),
        disabled: true,
    },
    {
        label: $gettext("Overwrite"),
        value: "overwrite",
        tooltip: $gettext(
            "If a Scheme or Concept already exists, replace it with the new one",
        ),
        disabled: false,
    },
]);

function updateFileValue(event: { files: File[] }) {
    if (event.files && event.files.length > 0) {
        file.value = event.files[0];
    } else {
        file.value = null;
    }
}

const isValid = computed(() => {
    return Boolean(file.value && overwriteOption.value);
});

async function submit() {
    if (!isValid.value || !file.value) {
        return;
    }
    loading.value = true;
    await importThesaurus(file.value, overwriteOption.value)
        .then(() => {
            emit("imported");
        })
        .catch((error: Error) => {
            toast.add({
                severity: ERROR,
                life: DEFAULT_ERROR_TOAST_LIFE,
                summary: $gettext("Unable to import SKOS file"),
                detail: error.message,
            });
            loading.value = false;
        });
}
</script>

<template>
    <Dialog
        v-model:visible="visible"
        position="center"
        :draggable="false"
        :header="$gettext('Import Lingo Resources from SKOS File')"
        :close-on-escape="true"
        :modal="true"
        :pt="{
            root: {
                style: {
                    minWidth: '40rem',
                    borderRadius: '0',
                    fontFamily: 'var(--p-lingo-font-family)',
                    fontSize: 'var(--p-lingo-font-size-small)',
                },
            },
            header: {
                style: {
                    background: 'var(--p-navigation-header-color)',
                    color: 'var(--p-dialog-header-text-color)',
                    borderRadius: '0',
                },
            },
        }"
    >
        <template #default>
            <ProgressSpinner
                v-if="loading"
                style="display: flex"
            />
            <div v-else>
                <div class="form-field">
                    <label for="skos-file-upload">{{
                        $gettext("SKOS File")
                    }}</label>
                    <InputFile
                        v-model="file"
                        accept=".xml"
                        mode="basic"
                        :auto="false"
                        :choose-label="$gettext('Choose File')"
                        :multiple="false"
                        :pt="{ input: { id: 'skos-file-upload' } }"
                        @select="updateFileValue"
                    />
                </div>
                <div class="form-field">
                    <label id="overwrite-options-label">{{
                        $gettext("Overwrite Options")
                    }}</label>
                    <div
                        role="radiogroup"
                        aria-labelledby="overwrite-options-label"
                    >
                        <span
                            v-for="option in overwriteOptions"
                            :key="option.value"
                            v-tooltip.bottom="{
                                value: option.tooltip,
                                showDelay: 1000,
                                hideDelay: 300,
                            }"
                            class="radio-button-and-label"
                        >
                            <RadioButton
                                v-model="overwriteOption"
                                :input-id="option.value"
                                :value="option.value"
                                :initial-value="option.value"
                                :aria-label="option.tooltip"
                                :invalid="!overwriteOption"
                                :disabled="option.disabled"
                            />
                            <label
                                :for="option.value"
                                class="radio-label"
                                >{{ option.label }}</label
                            >
                        </span>
                    </div>
                </div>
            </div>
        </template>
        <template #footer>
            <Button
                :label="$gettext('Cancel')"
                type="button"
                class="footer-button"
                @click="visible = false"
            />
            <Button
                :label="$gettext('Upload File')"
                type="submit"
                class="footer-button"
                :disabled="isValid === false || loading"
                @click="submit"
            />
        </template>
    </Dialog>
</template>
<style scoped>
.p-radiobutton {
    vertical-align: unset;
}
.p-fileupload-basic {
    justify-content: flex-start;
}
.form-field {
    margin-top: 1rem;
    padding-inline-start: 0.5rem;

    label {
        margin-bottom: 0;
    }
}
.radio-button-and-label {
    margin-right: 1.5rem;
    margin-bottom: 0.5rem;
}
.radio-label {
    margin-inline-start: 0.5rem;
}

:deep(.p-fileupload-choose-button),
.footer-button {
    font-size: var(--p-lingo-font-size-small);
}
</style>
