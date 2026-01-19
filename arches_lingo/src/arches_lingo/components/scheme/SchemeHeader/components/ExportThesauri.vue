<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import ProgressSpinner from "primevue/progressspinner";
import RadioButton from "primevue/radiobutton";

import { exportThesaurus } from "@/arches_lingo/api.ts";
import {
    DEFAULT_TOAST_LIFE,
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
} from "@/arches_lingo/constants.ts";

const { $gettext } = useGettext();
const toast = useToast();

const props = defineProps<{
    resourceId: string;
    resourceName: string | undefined;
}>();

const loading = ref(false);
const visible = ref(true);

const exportFormat = ref("xml");
const exportformatOptions = ref([
    { label: "csv", value: "csv", disabled: true },
    { label: "SKOS", value: "xml", disabled: false },
    { label: "rdf", value: "rdf", disabled: true },
    { label: "JSON-LD", value: "jsonld", disabled: true },
]);
const fileName = ref();

async function exportThesauri() {
    if (!exportFormat.value) {
        return;
    } else {
        loading.value = true;
        await exportThesaurus(
            props.resourceId,
            exportFormat.value,
            fileName.value || undefined,
        )
            .then(() => {
                toast.add({
                    severity: "success",
                    life: DEFAULT_TOAST_LIFE,
                    summary: $gettext("Export initiated"),
                    detail: $gettext(
                        "Your thesaurus export is being processed. You will be notified when it is complete.",
                    ),
                });
                visible.value = false;
            })
            .catch((error: Error) => {
                toast.add({
                    severity: ERROR,
                    life: DEFAULT_ERROR_TOAST_LIFE,
                    summary: $gettext("Unable to export thesaurus"),
                    detail: error.message,
                });
                loading.value = false;
            });
    }
}
</script>

<template>
    <Dialog
        v-model:visible="visible"
        position="center"
        :draggable="false"
        :header="$gettext('Export Thesauri')"
        :close-on-escape="true"
        :modal="true"
        :pt="{
            root: {
                style: {
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
                    paddingBlock: '1.25rem',
                    paddingInline: '1.5rem',
                },
            },
            title: {
                style: {
                    fontSize: 'var(--p-lingo-font-size-large)',
                    fontWeight: 'var(--p-lingo-font-weight-bold)',
                    lineHeight: '1.2',
                },
            },
            content: {
                style: {
                    padding: '1.25rem',
                    paddingTop: '1rem',
                },
            },
        }"
    >
        <template #default>
            <div
                v-if="loading"
                class="loading"
            >
                <ProgressSpinner />
            </div>

            <div
                v-else
                class="form"
            >
                <div class="field">
                    <label
                        id="export-format-select-label"
                        class="label"
                    >
                        {{ $gettext("Export Format") }}
                    </label>

                    <div
                        class="control"
                        role="radiogroup"
                        aria-labelledby="export-format-select-label"
                    >
                        <div class="radio-grid">
                            <span
                                v-for="option in exportformatOptions"
                                :key="option.value"
                                class="radio-option"
                            >
                                <RadioButton
                                    v-model="exportFormat"
                                    :input-id="option.value"
                                    :value="option.value"
                                    :disabled="option.disabled"
                                />
                                <label
                                    :for="option.value"
                                    class="radio-label"
                                >
                                    {{ option.label }}
                                </label>
                            </span>
                        </div>
                    </div>
                </div>

                <div class="field">
                    <label
                        class="label"
                        for="file-name-input"
                    >
                        {{ $gettext("File Name (optional)") }}
                    </label>

                    <div class="control">
                        <InputText
                            id="file-name-input"
                            v-model="fileName"
                            :placeholder="$gettext('Enter file name')"
                            class="text-input"
                        />
                    </div>
                </div>
            </div>
        </template>

        <template #footer>
            <div class="footer">
                <Button
                    icon="pi pi-times"
                    :label="$gettext('Cancel')"
                    type="button"
                    severity="danger"
                    class="footer-button"
                    @click="visible = false"
                />
                <Button
                    icon="pi pi-file-export"
                    :label="$gettext('Export')"
                    type="submit"
                    class="footer-button"
                    :disabled="!exportFormat || loading"
                    :loading="loading"
                    @click="exportThesauri"
                />
            </div>
        </template>
    </Dialog>
</template>

<style scoped>
.form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.field {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.label {
    display: block;
    margin: 0;
    font-weight: var(--p-lingo-font-weight-bold);
}

.control {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.radio-grid {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    border: 1px solid var(--p-content-border-color);
    border-radius: var(--p-border-radius);
    background: var(--p-content-background);
}

.radio-option {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    white-space: nowrap;
}

.radio-label {
    margin: 0;
    cursor: pointer;
}

.text-input {
    width: 100%;
}

.footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
}

.footer-button {
    font-size: var(--p-lingo-font-size-small);
}

.loading {
    display: flex;
    align-items: center;
    justify-content: center;
}
</style>
