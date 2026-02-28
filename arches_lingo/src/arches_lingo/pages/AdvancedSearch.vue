<script setup lang="ts">
import { onMounted, ref, useTemplateRef } from "vue";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Panel from "primevue/panel";
import Splitter from "primevue/splitter";
import SplitterPanel from "primevue/splitterpanel";

import FacetGroup from "@/arches_lingo/components/advanced-search/FacetGroup.vue";
import SearchResults from "@/arches_lingo/components/advanced-search/SearchResults.vue";
import SavedSearches from "@/arches_lingo/components/advanced-search/SavedSearches.vue";
import ConceptSets from "@/arches_lingo/components/advanced-search/ConceptSets.vue";

import {
    executeAdvancedSearch,
    fetchAdvancedSearchOptions,
    fetchControlledListOptions,
} from "@/arches_lingo/api.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    LABEL_TYPE_LIST_ID,
    NOTE_TYPE_LIST_ID,
    CONCEPT_TYPE_LIST_ID,
} from "@/arches_lingo/constants.ts";

import type {
    AdvancedSearchOptions,
    AdvancedSearchQuery,
    AdvancedSearchResponse,
    ConceptSetItem,
    ControlledListOption,
    SearchCondition,
    SearchGroup,
} from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();
const toast = useToast();

const conceptSetsRef =
    useTemplateRef<InstanceType<typeof ConceptSets>>("conceptSetsRef");

let nextId = Date.now();
function generateId(): string {
    return `cond-${nextId++}`;
}

// ── State ──────────────────────────────────────────────────────

const searchOptions = ref<AdvancedSearchOptions>({
    languages: [],
    schemes: [],
    lifecycle_states: [],
    label_types: [],
    note_types: [],
    concept_types: [],
});

const conceptSets = ref<ConceptSetItem[]>([]);

const queryGroup = ref<SearchGroup>({
    id: generateId(),
    operator: "and",
    conditions: [
        {
            id: generateId(),
            facet: "label",
            value: "",
        } as SearchCondition,
    ],
});

const searchResults = ref<AdvancedSearchResponse | null>(null);
const isSearching = ref(false);
const currentPage = ref(1);
const selectedConceptIds = ref<Set<string>>(new Set());
const activeConceptSetId = ref<number | null>(null);
const showSidePanel = ref(true);

// ── Search Options ─────────────────────────────────────────────

interface ControlledListItem {
    id: string;
    values: { valuetype_id: string; value: string }[];
    children?: ControlledListItem[];
}

function getPreferredLabel(item: ControlledListItem): string {
    const pref = item.values?.find((v) => v.valuetype_id === "prefLabel");
    return pref?.value || item.values?.[0]?.value || item.id;
}

function flattenListItems(items: ControlledListItem[]): ControlledListOption[] {
    const result: ControlledListOption[] = [];
    for (const item of items) {
        result.push({ label: getPreferredLabel(item), value: item.id });
        if (item.children && Array.isArray(item.children)) {
            result.push(...flattenListItems(item.children));
        }
    }
    return result;
}

async function loadSearchOptions() {
    try {
        const [options, labelList, noteList, conceptTypeList] =
            await Promise.all([
                fetchAdvancedSearchOptions(),
                fetchControlledListOptions(LABEL_TYPE_LIST_ID),
                fetchControlledListOptions(NOTE_TYPE_LIST_ID),
                fetchControlledListOptions(CONCEPT_TYPE_LIST_ID),
            ]);

        searchOptions.value = {
            ...options,
            label_types: [],
            note_types: [],
            concept_types: [],
        };

        if (labelList?.items) {
            searchOptions.value.label_types = flattenListItems(labelList.items);
        }
        if (noteList?.items) {
            searchOptions.value.note_types = flattenListItems(noteList.items);
        }
        if (conceptTypeList?.items) {
            searchOptions.value.concept_types = flattenListItems(
                conceptTypeList.items,
            );
        }
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to load search options."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

// ── Search Execution ───────────────────────────────────────────

function buildQuery(): AdvancedSearchQuery {
    return {
        operator: queryGroup.value.operator,
        conditions: queryGroup.value.conditions,
    };
}

async function executeSearch(page: number = 1) {
    isSearching.value = true;
    currentPage.value = page;

    try {
        const query = buildQuery();
        searchResults.value = await executeAdvancedSearch(query, page, 25);
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Search failed."),
            detail: error instanceof Error ? error.message : undefined,
        });
        searchResults.value = null;
    } finally {
        isSearching.value = false;
    }
}

function clearSearch() {
    queryGroup.value = {
        id: generateId(),
        operator: "and",
        conditions: [
            {
                id: generateId(),
                facet: "label",
                value: "",
            } as SearchCondition,
        ],
    };
    searchResults.value = null;
    selectedConceptIds.value = new Set();
    currentPage.value = 1;
    activeConceptSetId.value = null;
}

// ── Selection ──────────────────────────────────────────────────

function toggleSelectConcept(id: string) {
    const newSet = new Set(selectedConceptIds.value);
    if (newSet.has(id)) {
        newSet.delete(id);
    } else {
        newSet.add(id);
    }
    selectedConceptIds.value = newSet;
}

function selectAll() {
    if (!searchResults.value) return;
    const newSet = new Set(selectedConceptIds.value);
    for (const item of searchResults.value.data) {
        newSet.add(item.id);
    }
    selectedConceptIds.value = newSet;
}

function deselectAll() {
    selectedConceptIds.value = new Set();
}

// ── Saved Searches ─────────────────────────────────────────────

function loadSavedSearch(query: AdvancedSearchQuery) {
    queryGroup.value = {
        id: generateId(),
        operator: query.operator,
        conditions: query.conditions,
    };
    searchResults.value = null;
    selectedConceptIds.value = new Set();
}

// ── Concept Sets ───────────────────────────────────────────────

function onSetsUpdated(sets: ConceptSetItem[]) {
    conceptSets.value = sets;
}

function loadConceptSet(conceptSetId: number) {
    activeConceptSetId.value = conceptSetId;
    queryGroup.value = {
        id: generateId(),
        operator: "and",
        conditions: [
            {
                id: generateId(),
                facet: "concept_set",
                value: String(conceptSetId),
            } as SearchCondition,
        ],
    };
    executeSearch(1);
}

function onConceptsRemoved() {
    executeSearch(currentPage.value);
}

// ── Lifecycle ──────────────────────────────────────────────────

onMounted(loadSearchOptions);
</script>

<template>
    <div class="advanced-search">
        <div class="search-header">
            <h2 class="search-header-title">
                <i
                    class="pi pi-search"
                    aria-hidden="true"
                />
                {{ $gettext("Advanced Search") }}
            </h2>
            <Button
                :label="
                    showSidePanel
                        ? $gettext('Hide Saved Searches & Sets')
                        : $gettext('Show Saved Searches & Sets')
                "
                :icon="
                    showSidePanel
                        ? 'pi pi-angle-double-right'
                        : 'pi pi-objects-column'
                "
                :class="'side-panel-toggle'"
                size="small"
                @click="showSidePanel = !showSidePanel"
            />
        </div>

        <Splitter
            class="search-splitter"
            :pt="{
                gutter: {
                    style: {
                        display: showSidePanel ? 'flex' : 'none',
                    },
                },
            }"
        >
            <SplitterPanel :size="75">
                <div class="search-content">
                    <!-- Query Builder Section -->
                    <div class="query-panel">
                        <FacetGroup
                            :group="queryGroup"
                            :options="searchOptions"
                            :concept-sets="conceptSets"
                            :depth="0"
                            @update:group="queryGroup = $event"
                        />

                        <div class="search-actions">
                            <Button
                                :label="$gettext('Search')"
                                icon="pi pi-search"
                                :loading="isSearching"
                                @click="executeSearch(1)"
                            />
                            <Button
                                :label="$gettext('Clear')"
                                icon="pi pi-eraser"
                                severity="secondary"
                                outlined
                                @click="clearSearch"
                            />
                        </div>
                    </div>

                    <!-- Search Results Section -->
                    <Panel
                        v-if="searchResults || isSearching"
                        :header="$gettext('Results')"
                        class="results-panel"
                    >
                        <SearchResults
                            :results="searchResults"
                            :loading="isSearching"
                            :selected-ids="selectedConceptIds"
                            @page-change="executeSearch($event)"
                            @toggle-select="toggleSelectConcept"
                            @select-all="selectAll"
                            @deselect-all="deselectAll"
                        />
                    </Panel>
                </div>
            </SplitterPanel>

            <SplitterPanel
                v-show="showSidePanel"
                :size="25"
            >
                <div class="side-panel">
                    <Panel
                        :header="$gettext('Saved')"
                        toggleable
                        class="side-section"
                    >
                        <SavedSearches
                            :current-query="buildQuery()"
                            @load-search="loadSavedSearch"
                        />
                    </Panel>

                    <Panel
                        :header="$gettext('Concept Sets')"
                        toggleable
                        class="side-section"
                    >
                        <ConceptSets
                            ref="conceptSetsRef"
                            :selected-concept-ids="selectedConceptIds"
                            :active-concept-set-id="activeConceptSetId"
                            @load-set="loadConceptSet"
                            @sets-updated="onSetsUpdated"
                            @concepts-removed="onConceptsRemoved"
                        />
                    </Panel>
                </div>
            </SplitterPanel>
        </Splitter>
    </div>
</template>

<style scoped>
.advanced-search {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    font-family: var(--p-lingo-font-family);
}

/* ── Header (matches concept-header-toolbar) ── */
.search-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    row-gap: 0.5rem;
    min-height: 3rem;
    padding: 0.375rem 1rem;
    background: var(--p-header-toolbar-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    flex-shrink: 0;
    box-sizing: border-box;
}

.search-header-title {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    margin: 0;
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-text-color);
}

.search-header-title .pi {
    font-size: var(--p-lingo-font-size-medium);
}

.side-panel-toggle {
    font-size: var(--p-lingo-font-size-small) !important;
    font-weight: var(--p-lingo-font-weight-normal) !important;
    border-radius: 0.125rem !important;
    background: var(--p-header-button-background) !important;
    color: var(--p-header-button-color) !important;
    border-color: var(--p-header-button-border) !important;
    border-style: solid !important;
    border-width: 0.0625rem !important;
}

.side-panel-toggle:hover {
    background: var(--p-highlight-background) !important;
}

/* ── Splitter ── */
.search-splitter {
    flex: 1 1 auto;
    border: none;
    overflow: hidden;
    border-radius: 0;
}

/* ── Main content area ── */
.search-content {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1rem;
    height: 100%;
    overflow: hidden;
}

/* ── Query builder panel ── */
.query-panel {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    flex-shrink: 0;
}

/* ── Search / Clear buttons ── */
.search-actions {
    display: flex;
    gap: 0.375rem;
    padding-top: 0.75rem;
    border-top: 0.0625rem solid var(--p-highlight-focus-background);
}

.search-actions :deep(.p-button) {
    font-size: var(--p-lingo-font-size-small);
    font-weight: var(--p-lingo-font-weight-normal);
    border-radius: 0.125rem;
}

/* ── Results panel ── */
.results-panel {
    flex: 1 1 auto;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    min-height: 0;
}

.results-panel :deep(.p-panel-header) {
    font-size: var(--p-lingo-font-size-medium);
    font-weight: var(--p-lingo-font-weight-normal);
    border-radius: 0.125rem 0.125rem 0 0;
    flex-shrink: 0;
}

.results-panel :deep(.p-panel-content-container) {
    flex: 1 1 auto;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.results-panel :deep(.p-panel-content) {
    flex: 1 1 auto;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    min-height: 0;
}

/* ── Side panel ── */
.side-panel {
    display: flex;
    flex-direction: column;
    gap: 0;
    height: 100%;
    overflow: auto;
}

.side-section {
    flex-shrink: 0;
}

.side-section :deep(.p-panel) {
    border-radius: 0.125rem;
}

.side-section :deep(.p-panel-header) {
    font-size: var(--p-lingo-font-size-medium);
    font-weight: var(--p-lingo-font-weight-normal);
}

/* ── Global overrides for all buttons inside advanced search ── */
.advanced-search :deep(.p-button) {
    border-radius: 0.125rem;
    font-family: var(--p-lingo-font-family);
}

/* ── Global overrides for inputs / dropdowns inside advanced search ── */
.advanced-search :deep(.p-select),
.advanced-search :deep(.p-inputtext),
.advanced-search :deep(.p-textarea),
.advanced-search :deep(.p-dropdown),
.advanced-search :deep(.p-multiselect) {
    border-radius: 0.125rem;
}

/* ── Panel border-radius ── */
.advanced-search :deep(.p-panel) {
    border-radius: 0.125rem;
}

.advanced-search :deep(.p-panel-header) {
    border-radius: 0.125rem 0.125rem 0 0;
}

.advanced-search :deep(.p-panel-content) {
    border-radius: 0 0 0.125rem 0.125rem;
}

/* ── Dialog border-radius ── */
.advanced-search :deep(.p-dialog) {
    border-radius: 0.125rem;
}

.advanced-search :deep(.p-dialog .p-button) {
    border-radius: 0.125rem;
}
</style>
