<script setup lang="ts">
import { computed, ref } from "vue";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Popover from "primevue/popover";
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

const exportDialog = ref();
const toggle = (event: Event) => {
    exportDialog.value.toggle(event);
};

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
                exportDialog.value.toggle();
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
    <!-- Placeholder export button -->
    <Button
        :aria-label="$gettext('Export')"
        class="add-button"
        @click="toggle"
    >
        <span><i class="pi pi-cloud-download"></i></span>
        <span>{{ $gettext("Export") }}</span>
    </Button>
    <Popover
        ref="exportDialog"
        class="export-panel"
    >
        <div class="exports-panel-container">
            <div class="container-title">
                <h3>
                    {{ $gettext("Export Thesaurus") }}
                </h3>
            </div>
            <div class="options-container">
                <h4>
                    {{ $gettext("Hierarchy Options") }}
                </h4>
                <SelectButton
                    v-model="exportDepth"
                    :options="exportDepthOptions"
                    option-label="label"
                    option-value="value"
                    option-disabled="disabled"
                />
            </div>
            <div class="formats-container">
                <h4>
                    {{ $gettext("Export Format") }}
                </h4>
                <div>
                    <span
                        v-for="option in exportformatOptions"
                        :key="option.value"
                        class="selection"
                    >
                        <RadioButton
                            :key="option.value"
                            v-model="exportFormat"
                            :input-id="option.value"
                            :value="option.value"
                            :label="option.label"
                        ></RadioButton>
                        <label :for="option.value">{{ option.label }}</label>
                    </span>
                </div>
            </div>
            <div class="file-name-container">
                <h4>
                    {{ $gettext("File Name (optional)") }}
                </h4>
                <InputText
                    v-model="fileName"
                    :placeholder="$gettext('Enter file name')"
                />
            </div>
            <div class="export-footer">
                <Button
                    icon="pi pi-trash"
                    :label="$gettext('Cancel')"
                ></Button>
                <Button
                    icon="pi pi-file-export"
                    :label="$gettext('Export')"
                    :disabled="isValid === false || loading"
                    @click="exportThesauri"
                ></Button>
            </div>
        </div>
    </Popover>
</template>

<style scoped>
.export-panel {
    padding: 1rem;
}

.exports-panel-container {
    font-family: var(--p-lingo-font-family);
    font-weight: 300;
    padding: 0 1rem;
}

.container-title {
    font-size: var(--p-lingo-font-size-normal);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    margin-bottom: 0.5rem;
}

.container-title h3 {
    padding-top: 0.5rem;
    margin: 0rem 0rem 0.25rem 0rem;
    font-weight: var(--p-lingo-font-weight-normal);
}

.options-container {
    padding: 0 0 0.75rem 0;
}

.options-container h4,
.file-name-container h4 {
    margin: 0;
    padding-bottom: 0.4rem;
}

.formats-container {
    padding: 0 0 0.75rem 0;
}

.formats-container h4 {
    margin: 0;
}

.selection {
    display: flex;
    gap: 0.5rem;
    padding: 0.2rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    align-items: center;
    color: var(--p-list-option-icon-color);
}

.export-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.25rem;
    border-top: 0.0625rem solid var(--p-header-toolbar-border);
    padding: 0.5rem 0 0 0;
}
</style>
