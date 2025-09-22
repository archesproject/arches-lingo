<script setup lang="ts">
import { ref } from "vue";

import Button from "primevue/button";
import SelectButton from "primevue/selectbutton";
import RadioButton from "primevue/radiobutton";
import Popover from "primevue/popover";

import type { ResourceInstanceResult } from "@/arches_lingo/types.ts";

const props = defineProps<{
    resource: ResourceInstanceResult;
}>();
console.log(props.resource);

//Placeholder for export button panel
const exportDialog = ref();
const toggle = (event: Event) => {
    exportDialog.value.toggle(event);
};

//Placeholder for export type
const exporter = ref("Concept Only");
const exporterOptions = ref(["Concept Only", "Concept + Children"]);

//Placeholder for export format radio button group
const exportFormat = ref();
const exportformatOptions = ref([
    { label: "csv", value: "csv" },
    { label: "SKOS", value: "skos" },
    { label: "rdf", value: "rdf" },
    { label: "JSON-LD", value: "jsonld" },
]);
</script>

<template>
    <!-- Placeholder export button -->
    <Button
        :aria-label="$gettext('Export')"
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
                    {{ $gettext("{SCHEME OR CONCEPT} Export") }}
                </h3>
            </div>
            <div class="options-container">
                <h4>
                    {{ $gettext("Export Options") }}
                </h4>
                <!-- TODO: export options go here -->
                <SelectButton
                    v-model="exporter"
                    :options="exporterOptions"
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
            <div class="export-footer">
                <Button
                    icon="pi pi-trash"
                    :label="$gettext('Export')"
                ></Button>
                <Button
                    icon="pi pi-trash"
                    :label="$gettext('Cancel')"
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

.options-container h4 {
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
    flex-direction: row-reverse;
    gap: 0.25rem;
    border-top: 0.0625rem solid var(--p-header-toolbar-border);
    padding: 0.5rem 0 0 0;
}
</style>
