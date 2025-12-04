<script setup lang="ts">
import { computed, ref } from "vue";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import ProgressSpinner from "primevue/progressspinner";
import RadioButton from "primevue/radiobutton";
import SelectButton from "primevue/selectbutton";

import { exportThesaurus } from "@/arches_lingo/api.ts";
import {
    DEFAULT_TOAST_LIFE,
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
} from "@/arches_lingo/constants.ts";
import type { ResourceInstanceResult } from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();
const toast = useToast();

const props = defineProps<{
    resource: ResourceInstanceResult;
}>();
console.log(props.resource);

const loading = ref(false);
const visible = ref(false);

const exportDepth = ref("complete");
const exportDepthOptions = ref([
    {
        label: $gettext("Complete Thesaurus"),
        value: "complete",
        disabled: false,
    },
    {
        label: $gettext("Concept Only"),
        value: "individual",
        disabled: true,
    },
]);
const exportFormat = ref("xml");
const exportformatOptions = ref([
    { label: "csv", value: "csv", disabled: true },
    { label: "SKOS", value: "xml", disabled: false },
    { label: "rdf", value: "rdf", disabled: true },
    { label: "JSON-LD", value: "jsonld", disabled: true },
]);
const fileName = ref();
const isValid = computed(() => {
    return Boolean(exportDepth.value && exportFormat.value);
});

async function exportThesauri() {
    if (!exportDepth.value || !exportFormat.value) {
        return;
    } else {
        loading.value = true;
        await exportThesaurus(
            props.resource.resourceinstanceid,
            exportDepth.value,
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
    <Button
        :aria-label="$gettext('Export')"
        class="add-button"
        @click="visible = !visible"
    >
        <span><i class="pi pi-cloud-download"></i></span>
        <span>{{ $gettext("Export") }}</span>
    </Button>
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
            content: {
                style: {
                    paddingTop: '0.5rem',
                },
            },
        }"
    >
        <template #default>
            <ProgressSpinner
                v-if="loading"
                style="display: flex"
            />
            <div class="form-item-container">
                <label
                    id="export-depth-select-label"
                    class="form-item-label"
                >
                    {{ $gettext("Hierarchy Options") }}
                </label>
                <SelectButton
                    id="export-depth-select"
                    v-model="exportDepth"
                    :options="exportDepthOptions"
                    option-label="label"
                    option-value="value"
                    option-disabled="disabled"
                    aria-labelledby="export-depth-select-label"
                    class="selection-button"
                />
            </div>
            <div class="form-item-container">
                <label
                    id="export-format-select-label"
                    class="form-item-label"
                >
                    {{ $gettext("Export Format") }}
                </label>
                <div role="radiogroup">
                    <span
                        v-for="option in exportformatOptions"
                        :key="option.value"
                        class="radio-button-and-label"
                    >
                        <RadioButton
                            :key="option.value"
                            v-model="exportFormat"
                            :input-id="option.value"
                            :value="option.value"
                            :label="option.label"
                            aria-labelledby="export-format-select-label"
                        ></RadioButton>
                        <label
                            :for="option.value"
                            class="radio-label"
                            >{{ option.label }}</label
                        >
                    </span>
                </div>
            </div>
            <div class="form-item-container">
                <label
                    class="form-item-label"
                    for="file-name-input"
                >
                    {{ $gettext("File Name (optional)") }}
                </label>
                <InputText
                    id="file-name-input"
                    v-model="fileName"
                    :placeholder="$gettext('Enter file name')"
                />
            </div>
        </template>
        <template #footer>
            <Button
                icon="pi pi-trash"
                :label="$gettext('Cancel')"
                type="button"
                class="footer-button"
                @click="visible = false"
            ></Button>
            <Button
                icon="pi pi-file-export"
                :label="$gettext('Export')"
                type="submit"
                class="footer-button"
                :disabled="isValid === false || loading"
                @click="exportThesauri"
            ></Button>
        </template>
    </Dialog>
</template>

<style scoped>
.form-item-container {
    margin-bottom: 0.75rem;
}
.form-item-label {
    display: block;
    margin-bottom: 0.25rem;
    font-weight: var(--p-lingo-font-weight-bold);
}
:deep(.p-selectbutton .p-togglebutton) {
    font-size: var(--p-lingo-font-size-small);
    margin: 0 0.5rem;
}
.p-radiobutton {
    vertical-align: unset;
}
.radio-button-and-label {
    margin-right: 1.5rem;
    margin-bottom: 0.5rem;
}
.radio-label {
    margin-inline-start: 0.5rem;
}
.footer-button {
    font-size: var(--p-lingo-font-size-small);
}
</style>
