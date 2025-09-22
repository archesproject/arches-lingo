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
                    class="add-button"
                ></Button>
                <Button
                    icon="pi pi-trash"
                    :label="$gettext('Cancel')"
                    class="add-button"
                ></Button>
            </div>
        </div>
    </Popover>
</template>
