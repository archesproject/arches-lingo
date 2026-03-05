<script setup lang="ts">
import { inject, ref, type Ref } from "vue";
import { useGettext } from "vue3-gettext";
import { useRouter } from "vue-router";

import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Paginator from "primevue/paginator";

import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { getParentLabels } from "@/arches_lingo/utils.ts";
import {
    selectedLanguageKey,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import type { Language } from "@/arches_component_lab/types.ts";

import type { AdvancedSearchResponse } from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();
const router = useRouter();

const systemLanguage = inject(systemLanguageKey) as Language;
const selectedLanguage = inject(selectedLanguageKey) as Ref<Language>;

defineProps<{
    results: AdvancedSearchResponse | null;
    loading: boolean;
    selectedIds: Set<string>;
}>();

const emit = defineEmits<{
    (event: "page-change", page: number): void;
    (event: "toggle-select", id: string): void;
    (event: "select-all"): void;
    (event: "deselect-all"): void;
}>();

const expandedRows = ref<Set<string>>(new Set());

function toggleExpand(id: string) {
    const newSet = new Set(expandedRows.value);
    if (newSet.has(id)) {
        newSet.delete(id);
    } else {
        newSet.add(id);
    }
    expandedRows.value = newSet;
}

function navigateToConcept(id: string) {
    router.push({
        name: routeNames.concept,
        params: { id },
    });
}

function onPageChange(event: { page: number }) {
    emit("page-change", event.page + 1);
}
</script>

<template>
    <div class="search-results">
        <div
            v-if="results"
            class="results-header"
        >
            <span class="results-count">
                {{
                    $gettext("%{count} results found", {
                        count: String(results.total_results),
                    })
                }}
            </span>
            <div class="results-actions">
                <Button
                    :label="$gettext('Select All')"
                    size="small"
                    text
                    @click="$emit('select-all')"
                />
                <Button
                    :label="$gettext('Deselect All')"
                    size="small"
                    text
                    @click="$emit('deselect-all')"
                />
            </div>
        </div>

        <div
            v-if="loading"
            class="loading-indicator"
        >
            <i class="pi pi-spin pi-spinner" />
            {{ $gettext("Searching...") }}
        </div>

        <div
            v-else-if="results && results.data.length === 0"
            class="no-results"
        >
            {{ $gettext("No results found.") }}
        </div>

        <div
            v-else-if="results"
            class="results-list"
        >
            <div
                v-for="item in results.data"
                :key="item.id"
                class="result-item"
            >
                <div class="result-row">
                    <Checkbox
                        :model-value="selectedIds.has(item.id)"
                        binary
                        @update:model-value="$emit('toggle-select', item.id)"
                    />

                    <Button
                        :icon="
                            expandedRows.has(item.id)
                                ? 'pi pi-chevron-down'
                                : 'pi pi-chevron-right'
                        "
                        text
                        rounded
                        size="small"
                        @click="toggleExpand(item.id)"
                    />

                    <div class="result-main">
                        <div class="result-label">
                            <i
                                class="pi pi-tag concept-icon"
                                aria-hidden="true"
                            />
                            {{
                                getItemLabel(
                                    item,
                                    selectedLanguage.code,
                                    systemLanguage.code,
                                ).value
                            }}
                        </div>
                        <div class="result-hierarchy">
                            [{{
                                getParentLabels(
                                    item,
                                    selectedLanguage.code,
                                    systemLanguage.code,
                                )
                            }}]
                        </div>
                        <div
                            v-if="item.uri"
                            class="result-uri"
                        >
                            {{ item.uri }}
                        </div>
                    </div>

                    <Button
                        :label="$gettext('View')"
                        icon="pi pi-arrow-right"
                        icon-pos="right"
                        size="small"
                        text
                        class="view-concept-button"
                        :aria-label="
                            $gettext('View concept %{label}', {
                                label: getItemLabel(
                                    item,
                                    selectedLanguage.code,
                                    systemLanguage.code,
                                ).value,
                            })
                        "
                        @click="navigateToConcept(item.id)"
                    />
                </div>

                <div
                    v-if="expandedRows.has(item.id)"
                    class="result-details"
                >
                    <div
                        v-if="item.identifier"
                        class="detail-row"
                    >
                        <span class="detail-label">{{
                            $gettext("Identifier:")
                        }}</span>
                        <span>{{ item.identifier }}</span>
                    </div>

                    <div
                        v-if="item.lifecycle_state"
                        class="detail-row"
                    >
                        <span class="detail-label">{{
                            $gettext("Lifecycle:")
                        }}</span>
                        <span>{{ item.lifecycle_state }}</span>
                    </div>

                    <div
                        v-if="item.notes && item.notes.length > 0"
                        class="detail-section"
                    >
                        <span class="detail-label">{{
                            $gettext("Notes:")
                        }}</span>
                        <div
                            v-for="(note, noteIdx) in item.notes"
                            :key="noteIdx"
                            class="note-item"
                        >
                            <span
                                v-if="note.type"
                                class="note-type"
                                >{{ note.type }}</span
                            >
                            <span
                                v-if="note.language"
                                class="note-language"
                                >[{{ note.language }}]</span
                            >
                            <span class="note-content">{{ note.content }}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <Paginator
            v-if="results && results.total_pages > 1"
            :rows="results.results_per_page"
            :total-records="results.total_results"
            :first="(results.current_page - 1) * results.results_per_page"
            @page="onPageChange"
        />
    </div>
</template>

<style scoped>
.search-results {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    font-family: var(--p-lingo-font-family);
    flex: 1 1 auto;
    overflow: hidden;
    min-height: 0;
}

.results-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0;
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
    flex-shrink: 0;
}

.results-count {
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-color);
}

.results-actions {
    display: flex;
    gap: 0.25rem;
}

.results-actions :deep(.p-button) {
    font-size: var(--p-lingo-font-size-xsmall);
    border-radius: 0.125rem;
}

.loading-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 2rem;
    color: var(--p-text-muted-color);
    font-size: var(--p-lingo-font-size-small);
}

.no-results {
    text-align: center;
    padding: 2rem;
    color: var(--p-text-muted-color);
    font-size: var(--p-lingo-font-size-small);
}

.results-list {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    overflow-y: auto;
    min-height: 0;
    border: 0.0625rem solid var(--p-highlight-focus-background);
    border-radius: 0.125rem;
}

:deep(.p-paginator) {
    flex-shrink: 0;
}

.result-item {
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
}

.result-item:hover {
    background-color: var(--p-highlight-background);
}

.result-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.25rem;
}

.result-main {
    flex: 1;
    min-width: 0;
}

.result-label {
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-normal);
}

.concept-icon {
    font-size: 0.625rem;
    margin-right: 0.25rem;
}

.result-hierarchy {
    font-size: var(--p-lingo-font-size-xsmall);
    color: var(--p-text-muted-color);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.result-uri {
    font-size: var(--p-lingo-font-size-xsmall);
    color: var(--p-primary-500);
    overflow-wrap: break-word;
    word-break: break-all;
    margin-top: 0.125rem;
}

.view-concept-button {
    flex-shrink: 0;
}

.view-concept-button :deep(.p-button) {
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
}

.result-details {
    padding: 0.5rem 0.75rem 0.75rem 3.5rem;
    background-color: var(--p-highlight-background);
    font-size: var(--p-lingo-font-size-small);
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
}

.detail-row {
    display: flex;
    gap: 0.5rem;
}

.detail-label {
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-500);
    flex-shrink: 0;
}

.detail-section {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.note-item {
    padding-left: 0.75rem;
    display: flex;
    gap: 0.375rem;
    flex-wrap: wrap;
}

.note-type {
    font-style: italic;
    color: var(--p-primary-500);
}

.note-language {
    color: var(--p-text-muted-color);
    font-size: var(--p-lingo-font-size-xsmall);
}

.note-content {
    word-break: break-word;
}
</style>
