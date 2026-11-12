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
import { generateArchesURL } from "@/arches/utils/generate-arches-url.ts";
import {
    DEFAULT_TOAST_LIFE,
    DEFAULT_ERROR_TOAST_LIFE,
    QUEUED_EXPORT_TOAST_LIFE,
    ERROR,
    INFO,
    SUCCESS,
} from "@/arches_lingo/constants.ts";

import type { ExportedFile } from "@/arches_lingo/types.ts";

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
    { label: "SKOS/XML", value: "xml", disabled: false },
    { label: "Turtle", value: "ttl", disabled: false },
    { label: "N-Triples", value: "nt", disabled: false },
    { label: "RDF/XML", value: "rdf", disabled: false },
    { label: "CSV", value: "csv", disabled: false },
    { label: "JSON-LD", value: "jsonld", disabled: false },
]);
const fileName = ref();

function downloadExportedFile(exportedFile: ExportedFile) {
    // The temp file endpoint responds with Content-Disposition: attachment,
    // so following the link downloads the file without leaving the page.
    const downloadLink = document.createElement("a");
    downloadLink.href = generateArchesURL("arches:temp_file", {
        file_id: exportedFile.fileid,
    });
    downloadLink.download = exportedFile.name;
    document.body.appendChild(downloadLink);
    downloadLink.click();
    downloadLink.remove();
}

function notifyExportQueued() {
    toast.add({
        severity: INFO,
        life: QUEUED_EXPORT_TOAST_LIFE,
        summary: $gettext("Export queued"),
        detail: $gettext(
            "This thesaurus is large, so it is being exported in the background. A download link will appear in the Notifications panel when it is ready.",
        ),
    });
}

function notifyExportComplete(exportedFile: ExportedFile | null) {
    toast.add({
        severity: SUCCESS,
        life: DEFAULT_TOAST_LIFE,
        summary: $gettext("Export complete"),
        detail: exportedFile
            ? $gettext(
                  "Your download of %{fileName} should begin automatically. It is also available in the Notifications panel.",
                  { fileName: exportedFile.name },
              )
            : $gettext(
                  "Your export is ready to download from the Notifications panel.",
              ),
    });
}

async function exportThesauri() {
    if (!exportFormat.value) {
        return;
    }

    loading.value = true;
    try {
        const exportResponse = await exportThesaurus(
            props.resourceId,
            exportFormat.value,
            fileName.value || undefined,
        );

        if (exportResponse.status === "queued") {
            notifyExportQueued();
        } else {
            if (exportResponse.file) {
                downloadExportedFile(exportResponse.file);
            }
            notifyExportComplete(exportResponse.file);
        }
        visible.value = false;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to export thesaurus"),
            detail:
                (error as Error).message ||
                $gettext("An unexpected error occurred during export."),
        });
    } finally {
        loading.value = false;
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
                    fontFamily: 'var(--p-lingo-font-family)',
                    fontSize: 'var(--p-lingo-font-size-small)',
                    border: '0.125rem solid var(--p-dialog-color)',
                    borderRadius: '0.25rem',
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
                    fontWeight: 'var(--p-lingo-font-weight-normal)',
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
                role="status"
                aria-live="polite"
            >
                <ProgressSpinner
                    style="width: 3rem; height: 3rem"
                    stroke-width="4"
                    aria-hidden="true"
                />
                <span class="loading-message">
                    {{
                        $gettext(
                            "Preparing your export. This may take a moment for larger thesauri.",
                        )
                    }}
                </span>
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
    font-weight: var(--p-lingo-font-weight-normal);
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

:deep(.p-inputtext) {
    font-size: 0.875rem !important;
}

.footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
}

.footer-button {
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
}

.loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    padding-block: 1rem;
    text-align: center;
}

.loading-message {
    color: var(--p-text-muted-color);
}

:deep(.p-dialog) {
    border: 0.125rem solid #000 !important;
}
</style>
