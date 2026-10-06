<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { useGettext } from "vue3-gettext";

import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";

import SearchResult from "@/arches_lingo/components/basic-search/SearchResult.vue";

import { fetchConceptResources } from "@/arches_lingo/api.ts";
import { EDITING_LIFECYCLE_STATE_ID, ERROR } from "@/arches_lingo/constants.ts";

import type { SearchResultItem } from "@/arches_lingo/types.ts";

const ITEMS_PER_PAGE = 25;
const SEARCH_DEBOUNCE_MILLISECONDS = 300;

const { schemeId, survivorConceptId, selectedConceptId } = defineProps<{
    schemeId: string;
    survivorConceptId: string;
    selectedConceptId: string | undefined;
}>();

const emit = defineEmits<{
    (event: "select", concept: SearchResultItem): void;
}>();

const { $gettext } = useGettext();

const searchTerm = ref("");
const candidates = ref<SearchResultItem[]>([]);
const isLoading = ref(false);
const fetchError = ref<string | null>(null);
let debounceTimeout: ReturnType<typeof setTimeout> | undefined;

// Responses can arrive out of order, so only the most recent request may write
// anything. FacetRow guards the same endpoint this way.
let activeRequestId = 0;

const trimmedSearchTerm = computed(function () {
    return searchTerm.value.trim();
});

const searchIconClass = computed(function () {
    if (isLoading.value) {
        return "pi pi-spinner pi-spin";
    }
    return "pi pi-search";
});

watch(trimmedSearchTerm, function (term) {
    discardPendingSearch();

    // An empty box searches for nothing rather than for everything, the same way
    // Lingo's own search clears its results.
    if (!term) {
        candidates.value = [];
        fetchError.value = null;
        isLoading.value = false;
        return;
    }

    debounceTimeout = setTimeout(fetchCandidates, SEARCH_DEBOUNCE_MILLISECONDS);
});

onBeforeUnmount(discardPendingSearch);

// Every lineage a search result carries begins with its scheme.
function getCandidateSchemeId(candidate: SearchResultItem) {
    return candidate.parents?.[0]?.[0]?.id;
}

// A merge within the survivor's scheme retires the absorbed concept, which only
// the Editing state allows. Across schemes the concept is only read from, so any
// state can be absorbed. The server enforces both.
function isMergeable(candidate: SearchResultItem) {
    return (
        getCandidateSchemeId(candidate) !== schemeId ||
        candidate.resource_instance_lifecycle_state_id ===
            EDITING_LIFECYCLE_STATE_ID
    );
}

function onCandidateClick(candidate: SearchResultItem) {
    if (isMergeable(candidate)) {
        emit("select", candidate);
    }
}

async function fetchCandidates() {
    const requestId = ++activeRequestId;
    isLoading.value = true;
    fetchError.value = null;
    try {
        const parsedResponse = await fetchConceptResources(
            trimmedSearchTerm.value,
            ITEMS_PER_PAGE,
            1,
            "",
            [survivorConceptId],
        );
        if (requestId !== activeRequestId) {
            return;
        }
        candidates.value = parsedResponse.data;
    } catch (error) {
        if (requestId !== activeRequestId) {
            return;
        }
        fetchError.value =
            error instanceof Error ? error.message : String(error);
    } finally {
        if (requestId === activeRequestId) {
            isLoading.value = false;
        }
    }
}

function discardPendingSearch() {
    clearTimeout(debounceTimeout);
    activeRequestId++;
}
</script>

<template>
    <div class="merge-picker">
        <IconField>
            <InputIcon :class="searchIconClass" />
            <InputText
                v-model="searchTerm"
                class="merge-picker-input"
                :placeholder="$gettext('Search concepts')"
                :aria-label="$gettext('Search concepts to merge')"
            />
        </IconField>

        <Message
            v-if="fetchError"
            :severity="ERROR"
            :closable="false"
        >
            {{ fetchError }}
        </Message>

        <p
            v-if="!trimmedSearchTerm"
            class="merge-picker-status"
        >
            {{ $gettext("Search for the concept you want to merge away.") }}
        </p>

        <p
            v-else-if="isLoading && !candidates.length"
            class="merge-picker-status"
        >
            {{ $gettext("Searching…") }}
        </p>

        <p
            v-else-if="!fetchError && !candidates.length"
            class="merge-picker-status"
        >
            {{ $gettext("No matching concepts.") }}
        </p>

        <ul
            v-else-if="candidates.length"
            class="merge-picker-results"
        >
            <li
                v-for="(candidate, index) in candidates"
                :key="candidate.id"
            >
                <button
                    type="button"
                    class="merge-picker-result"
                    :class="{ selected: candidate.id === selectedConceptId }"
                    :disabled="!isMergeable(candidate)"
                    @click="onCandidateClick(candidate)"
                >
                    <SearchResult
                        :search-result="{ index, option: candidate }"
                    />
                    <span
                        v-if="!isMergeable(candidate)"
                        class="merge-picker-result-reason"
                    >
                        {{
                            $gettext(
                                "Only a concept in the Editing state can be merged within this scheme, because it is retired afterwards.",
                            )
                        }}
                    </span>
                </button>
            </li>
        </ul>
    </div>
</template>

<style scoped>
.merge-picker {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    gap: 0.75rem;
}

.merge-picker-input {
    width: 100%;
    border-radius: 0.125rem;
    font-size: var(--p-lingo-font-size-small);
}

.merge-picker-status {
    display: flex;
    flex: 1;
    align-items: center;
    justify-content: center;
    min-height: 0;
    margin: 0;
    padding: 1rem;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.125rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
    text-align: center;
}

.merge-picker-results {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    margin: 0;
    padding: 0;
    list-style: none;
    overflow-y: auto;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.125rem;
}

.merge-picker-result {
    display: block;
    width: 100%;
    padding: 0;
    border: none;
    background: none;
    text-align: start;
    cursor: pointer;
}

.merge-picker-result:disabled {
    cursor: not-allowed;
}

.merge-picker-result:disabled :deep(.search-result) {
    opacity: 0.6;
}

.merge-picker-result-reason {
    display: block;
    padding: 0 1rem 0.5rem;
    font-size: var(--p-lingo-font-size-xsmall);
    color: var(--p-text-muted-color);
}

.merge-picker-result.selected :deep(.search-result) {
    background-color: var(--p-highlight-background);
    box-shadow: inset 0.1875rem 0 0 var(--p-primary-color);
}

.merge-picker-result:not(:disabled):hover :deep(.search-result) {
    background-color: var(--p-search-result-focus-background);
}
</style>
