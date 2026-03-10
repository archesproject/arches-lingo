<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Skeleton from "primevue/skeleton";
import Splitter from "primevue/splitter";
import SplitterPanel from "primevue/splitterpanel";
import Tag from "primevue/tag";
import { useToast } from "primevue/usetoast";

import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
} from "@/arches_controlled_lists/constants.ts";

import type {
    PaginatedResourceListResponse,
    ResourceSummary,
} from "@/arches_lingo/types";

const PAGE_SIZE = 25;

const props = defineProps<{
    pageTitle: string;
    fetchResources: (
        search: string,
        limit: number,
        offset: number,
    ) => Promise<PaginatedResourceListResponse>;
    showGraphType?: boolean;
    refreshTrigger?: number;
}>();

const emit = defineEmits<{
    "select-resource": [resource: ResourceSummary];
}>();

const toast = useToast();
const { $gettext } = useGettext();

const isLoading = ref(true);
const resources = ref<ResourceSummary[]>([]);
const totalRecords = ref(0);
const currentPage = ref(0);
const searchQuery = ref("");
const selectedResource = ref<ResourceSummary | null>(null);
const isEditorOpen = ref(false);
const isCreatingNew = ref(false);

let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

const editorTitle = computed(() => {
    if (isCreatingNew.value) return $gettext("New Resource");
    if (!selectedResource.value) return "";
    return selectedResource.value.display_name || $gettext("Untitled");
});

watch(
    () => props.fetchResources,
    () => {
        currentPage.value = 0;
        loadResources();
    },
    { immediate: true },
);

watch(
    () => props.refreshTrigger,
    () => {
        loadResources();
    },
);

async function loadResources() {
    isLoading.value = true;
    try {
        const response = await props.fetchResources(
            searchQuery.value,
            PAGE_SIZE,
            currentPage.value * PAGE_SIZE,
        );
        resources.value = response.results;
        totalRecords.value = response.count;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch resources"),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
    isLoading.value = false;
}

function onPage(event: { first: number; rows: number }) {
    currentPage.value = Math.floor(event.first / event.rows);
    loadResources();
}

function onSearchInput() {
    if (searchDebounceTimer) {
        clearTimeout(searchDebounceTimer);
    }
    searchDebounceTimer = setTimeout(() => {
        currentPage.value = 0;
        loadResources();
    }, 400);
}

function onRowSelect(event: { data: ResourceSummary }) {
    isCreatingNew.value = false;
    selectedResource.value = event.data;
    isEditorOpen.value = true;
    emit("select-resource", event.data);
}

function openBlankEditor() {
    selectedResource.value = null;
    isCreatingNew.value = true;
    isEditorOpen.value = true;
}

function closeEditor() {
    isEditorOpen.value = false;
    selectedResource.value = null;
    isCreatingNew.value = false;
}
</script>

<template>
    <div class="resource-list-editor">
        <Splitter class="resource-splitter">
            <SplitterPanel
                :size="isEditorOpen ? 50 : 100"
                :min-size="30"
                class="list-panel"
            >
                <div class="list-panel-content">
                    <div class="list-header">
                        <div class="list-header-toolbar">
                            <h1 class="page-title">{{ pageTitle }}</h1>
                            <div class="header-buttons">
                                <slot
                                    name="list-actions"
                                    :open-blank-editor="openBlankEditor"
                                />
                            </div>
                        </div>
                        <div class="list-header-content">
                            <IconField class="search-field">
                                <InputIcon class="pi pi-search" />
                                <InputText
                                    v-model="searchQuery"
                                    :placeholder="$gettext('Search by name...')"
                                    class="search-input"
                                    @input="onSearchInput"
                                />
                            </IconField>
                        </div>
                    </div>

                    <DataTable
                        v-model:selection="selectedResource"
                        :value="resources"
                        :loading="isLoading"
                        :lazy="true"
                        :paginator="true"
                        :rows="PAGE_SIZE"
                        :total-records="totalRecords"
                        :first="currentPage * PAGE_SIZE"
                        selection-mode="single"
                        data-key="resourceinstanceid"
                        striped-rows
                        class="resource-table"
                        @page="onPage"
                        @row-select="onRowSelect"
                    >
                        <Column
                            field="display_name"
                            :header="$gettext('Name')"
                            class="name-column"
                        >
                            <template #body="{ data }">
                                <span v-if="data.display_name">{{
                                    data.display_name
                                }}</span>
                                <span
                                    v-else
                                    class="unnamed-resource"
                                    >{{ $gettext("Untitled") }}</span
                                >
                            </template>
                            <template #loading>
                                <Skeleton />
                            </template>
                        </Column>

                        <Column
                            v-if="showGraphType"
                            field="graph_name"
                            :header="$gettext('Type')"
                            class="type-column"
                        >
                            <template #body="{ data }">
                                <Tag
                                    :value="data.graph_name"
                                    severity="info"
                                />
                            </template>
                            <template #loading>
                                <Skeleton />
                            </template>
                        </Column>

                        <template #empty>
                            <div class="empty-message">
                                {{
                                    searchQuery
                                        ? $gettext(
                                              "No resources match the search criteria.",
                                          )
                                        : $gettext(
                                              "No resources have been created yet.",
                                          )
                                }}
                            </div>
                        </template>
                    </DataTable>
                </div>
            </SplitterPanel>

            <SplitterPanel
                v-if="isEditorOpen"
                :size="50"
                :min-size="30"
                class="editor-panel"
            >
                <div class="editor-panel-content">
                    <div class="editor-header">
                        <h2 class="editor-title">{{ editorTitle }}</h2>
                        <div class="editor-controls">
                            <Button
                                :aria-label="$gettext('Close editor')"
                                class="panel-control-button"
                                @click="closeEditor"
                            >
                                <i
                                    class="pi pi-times"
                                    aria-hidden="true"
                                />
                            </Button>
                        </div>
                    </div>
                    <div class="editor-body">
                        <slot
                            name="editor"
                            :resource="selectedResource"
                            :is-creating-new="isCreatingNew"
                        />
                    </div>
                </div>
            </SplitterPanel>
        </Splitter>
    </div>
</template>

<style scoped>
.resource-list-editor {
    height: 100%;
    min-height: 0;
}

.resource-splitter {
    height: 100%;
    min-height: 0;
    border: none;
}

.list-panel {
    overflow: auto;
}

.list-panel-content {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
}

.list-header {
    display: flex;
    flex-direction: column;
}

.list-header-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--p-header-toolbar-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    padding: 0.375rem 1rem;
}

.header-buttons {
    display: flex;
    gap: 0.25rem;
    flex-wrap: wrap;
    justify-content: flex-end;
}

.list-header-content {
    padding: 0.75rem 1rem;
}

.page-title {
    margin: 0;
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
}

.search-field {
    width: 100%;
}

.search-input {
    width: 100%;
    border-radius: 0.125rem;
}

.resource-table {
    flex: 1;
    min-height: 0;
    padding: 0 1rem;
}

.unnamed-resource {
    color: var(--p-inputtext-placeholder-color);
    font-style: italic;
}

.empty-message {
    padding: 2rem;
    text-align: center;
    color: var(--p-inputtext-placeholder-color);
}

.editor-panel {
    overflow: auto;
}

.editor-panel-content {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
}

.editor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--p-header-toolbar-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    padding: 0 1rem;
    padding-bottom: 0.1rem;
}

.editor-title {
    margin: 0.75rem 0;
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.editor-controls {
    flex-shrink: 0;
}

.panel-control-button {
    border-radius: 50%;
    background: var(--p-primary-contrast-color);
    border: 0.0625rem solid var(--p-header-button-border);
    color: var(--p-editor-form-color);
}

.editor-body {
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem 1rem;
    background: var(--p-editor-form-background);
}

:deep(.type-column) {
    width: 8rem;
}

:deep(.p-inputtext),
:deep(.p-multiselect),
:deep(.p-textarea),
:deep(.p-treeselect),
:deep(.p-select) {
    border-radius: 0.125rem;
}

:deep(.p-inputtext) {
    font-size: 0.875rem !important;
}

:deep(.p-treeselect-label) {
    font-size: 0.875rem !important;
}
</style>
