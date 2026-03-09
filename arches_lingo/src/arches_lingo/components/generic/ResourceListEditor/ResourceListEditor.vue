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

defineExpose({ refreshList: loadResources, openBlankEditor });
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
                        <div class="list-header-top">
                            <h1 class="page-title">{{ pageTitle }}</h1>
                            <slot name="list-actions" />
                        </div>
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
                                <Skeleton
                                    width="12rem"
                                    height="1.25rem"
                                />
                            </template>
                        </Column>

                        <Column
                            v-if="showGraphType"
                            field="graph_name"
                            :header="$gettext('Type')"
                            style="width: 10rem"
                        >
                            <template #body="{ data }">
                                <Tag
                                    :value="data.graph_name"
                                    severity="info"
                                />
                            </template>
                            <template #loading>
                                <Skeleton
                                    width="6rem"
                                    height="1.25rem"
                                />
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
    padding: 1rem;
}

.list-header {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-bottom: 1rem;
}

.list-header-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.page-title {
    margin: 0;
    font-size: var(--p-lingo-font-size-large, 1.25rem);
    font-weight: var(--p-lingo-font-weight-normal, 600);
    color: var(--p-neutral-700);
}

.search-field {
    width: 100%;
    max-width: 24rem;
}

.search-input {
    width: 100%;
}

.resource-table {
    flex: 1;
    min-height: 0;
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
    padding: 1rem;
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
}

.editor-title {
    margin: 0;
    font-size: var(--p-lingo-font-size-medium, 1rem);
    font-weight: var(--p-lingo-font-weight-normal, 600);
    color: var(--p-neutral-700);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.editor-controls {
    flex-shrink: 0;
}

.panel-control-button {
    border-radius: 50%;
    height: 2.25rem;
    width: 2.25rem;
    background: var(--p-primary-contrast-color);
    border: 0.0625rem solid var(--p-header-button-border);
    color: var(--p-editor-form-color);
}

.editor-body {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
}

:deep(.name-column) {
    min-width: 12rem;
}
</style>
