<script setup lang="ts">
import { computed } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";

import type {
    SparqlResults,
    SparqlBindingValue,
} from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();

const props = defineProps<{
    results: SparqlResults | null;
    loading: boolean;
}>();

const emit = defineEmits<{
    (e: "download", format: string): void;
}>();

const columnHeaders = computed(() => {
    if (!props.results) return [];
    return props.results.head.vars;
});

const tableData = computed(() => {
    if (!props.results) return [];
    return props.results.results.bindings;
});

const resultCount = computed(() => {
    return tableData.value.length;
});

function formatCellValue(value: SparqlBindingValue | undefined): string {
    if (!value) return "";
    if (value.type === "uri") return value.value;
    let display = value.value;
    if (value["xml:lang"]) {
        display += ` @${value["xml:lang"]}`;
    }
    return display;
}

function isUri(value: SparqlBindingValue | undefined): boolean {
    return value?.type === "uri";
}

function getLingoLink(value: SparqlBindingValue): string | null {
    if (value.type !== "uri") return null;
    const uuidMatch = value.value.match(
        /([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/i,
    );
    if (uuidMatch) {
        return `/concept/${uuidMatch[1]}`;
    }
    return null;
}
</script>

<template>
    <div class="sparql-results">
        <div class="results-header">
            <span class="result-count">
                {{
                    $gettext("%{count} results", {
                        count: String(resultCount),
                    })
                }}
            </span>
            <div class="download-actions">
                <Button
                    :label="$gettext('CSV')"
                    icon="pi pi-download"
                    size="small"
                    severity="secondary"
                    @click="emit('download', 'csv')"
                />
                <Button
                    :label="$gettext('JSON')"
                    icon="pi pi-download"
                    size="small"
                    severity="secondary"
                    @click="emit('download', 'json')"
                />
            </div>
        </div>

        <DataTable
            :value="tableData"
            :loading="loading"
            scrollable
            scroll-height="flex"
            striped-rows
            size="small"
            class="results-table"
        >
            <Column
                v-for="header in columnHeaders"
                :key="header"
                :field="header"
                :header="header"
            >
                <template #body="{ data }">
                    <template v-if="isUri(data[header])">
                        <a
                            v-if="getLingoLink(data[header])"
                            :href="getLingoLink(data[header])!"
                            class="lingo-link"
                        >
                            {{ formatCellValue(data[header]) }}
                        </a>
                        <span
                            v-else
                            class="uri-value"
                        >
                            {{ formatCellValue(data[header]) }}
                        </span>
                    </template>
                    <span v-else>
                        {{ formatCellValue(data[header]) }}
                    </span>
                </template>
            </Column>

            <template #empty>
                <div class="empty-message">
                    {{ $gettext("No results found.") }}
                </div>
            </template>
        </DataTable>
    </div>
</template>

<style scoped>
.sparql-results {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    flex: 1 1 auto;
    overflow: hidden;
    min-height: 0;
}

.results-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
}

.result-count {
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-text-muted-color);
}

.download-actions {
    display: flex;
    gap: 0.25rem;
}

.results-table {
    flex: 1 1 auto;
    min-height: 0;
}

.results-table :deep(.p-datatable-header-cell) {
    font-size: var(--p-lingo-font-size-small);
    font-weight: var(--p-lingo-font-weight-semibold);
    white-space: nowrap;
}

.results-table :deep(.p-datatable-body-cell) {
    font-size: var(--p-lingo-font-size-small);
    font-family: "Courier New", Courier, monospace;
    max-width: 25rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.lingo-link {
    color: var(--p-primary-color);
    text-decoration: none;
}

.lingo-link:hover {
    text-decoration: underline;
}

.uri-value {
    color: var(--p-primary-color);
    opacity: 0.8;
}

.empty-message {
    text-align: center;
    padding: 2rem;
    color: var(--p-text-muted-color);
}
</style>
