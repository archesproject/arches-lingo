<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Select from "primevue/select";
import Textarea from "primevue/textarea";

import { fetchSparqlExamples } from "@/arches_lingo/api.ts";

import type { SparqlExample } from "@/arches_lingo/types.ts";

interface SchemeOption {
    id: string;
    labels: { value: string; language_id: string }[];
}

const { $gettext } = useGettext();

const props = defineProps<{
    schemes: SchemeOption[];
    isExecuting: boolean;
}>();

const emit = defineEmits<{
    (e: "execute", query: string, schemeId?: string): void;
}>();

const queryText = ref("");
const selectedSchemeId = ref<string | undefined>(undefined);
const exampleQueries = ref<SparqlExample[]>([]);

const schemeOptions = [
    { label: $gettext("All schemes"), value: undefined },
    ...props.schemes.map((scheme) => ({
        label: scheme.labels[0]?.value || scheme.id,
        value: scheme.id,
    })),
];

async function loadExamples() {
    try {
        exampleQueries.value = await fetchSparqlExamples();
    } catch {
        exampleQueries.value = [];
    }
}

function loadExample(example: SparqlExample) {
    queryText.value = example.query;
}

function executeQuery() {
    if (queryText.value.trim()) {
        emit("execute", queryText.value, selectedSchemeId.value);
    }
}

function clearQuery() {
    queryText.value = "";
}

function handleKeydown(event: KeyboardEvent) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        executeQuery();
    }
}

onMounted(loadExamples);
</script>

<template>
    <div class="sparql-editor">
        <div class="editor-toolbar">
            <div class="toolbar-left">
                <Select
                    v-if="exampleQueries.length"
                    :options="exampleQueries"
                    option-label="title"
                    :placeholder="$gettext('Load example query...')"
                    class="example-select"
                    @change="loadExample($event.value)"
                />
            </div>
            <div class="toolbar-right">
                <Select
                    :model-value="
                        schemeOptions.find(
                            (option) => option.value === selectedSchemeId,
                        )
                    "
                    :options="schemeOptions"
                    option-label="label"
                    :placeholder="$gettext('All schemes')"
                    class="scheme-select"
                    @change="selectedSchemeId = $event.value?.value"
                />
            </div>
        </div>

        <Textarea
            v-model="queryText"
            :placeholder="
                $gettext(
                    'Enter a SPARQL query...\n\nExample:\nPREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n\nSELECT ?concept ?label\nWHERE {\n    ?concept a skos:Concept ;\n             skos:prefLabel ?label .\n}',
                )
            "
            class="query-textarea"
            auto-resize
            @keydown="handleKeydown"
        />

        <div class="editor-actions">
            <Button
                :label="$gettext('Run Query')"
                icon="pi pi-play"
                :loading="props.isExecuting"
                :disabled="!queryText.trim()"
                @click="executeQuery"
            />
            <Button
                :label="$gettext('Clear')"
                icon="pi pi-eraser"
                severity="secondary"
                :disabled="!queryText"
                @click="clearQuery"
            />
            <span class="keyboard-hint">
                {{ $gettext("Ctrl+Enter to run") }}
            </span>
        </div>
    </div>
</template>

<style scoped>
.sparql-editor {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.editor-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.toolbar-left,
.toolbar-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.example-select {
    min-width: 14rem;
}

.scheme-select {
    min-width: 12rem;
}

.query-textarea {
    font-family: "Courier New", Courier, monospace;
    font-size: var(--p-lingo-font-size-small);
    min-height: 12rem;
    max-height: 25rem;
    line-height: 1.5;
    tab-size: 4;
    white-space: pre;
    overflow-wrap: normal;
    overflow-x: auto;
    border-radius: 0.125rem;
}

.editor-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.keyboard-hint {
    font-size: var(--p-lingo-font-size-xsmall);
    color: var(--p-text-muted-color);
    margin-left: auto;
}
</style>
