<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { useGettext } from "vue3-gettext";

import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";

import SearchResult from "@/arches_lingo/components/basic-search/SearchResult.vue";

import { fetchConceptResources } from "@/arches_lingo/api.ts";
import { EDITING_LIFECYCLE_STATE_ID, ERROR } from "@/arches_lingo/constants.ts";

import type { SearchResultItem } from "@/arches_lingo/types.ts";

const { schemeId, survivorConceptId, selectedConceptId } = defineProps<{
    schemeId: string;
    survivorConceptId: string;
    selectedConceptId: string | undefined;
}>();

const emit = defineEmits<{
    (event: "select", concept: SearchResultItem): void;
}>();

const { $gettext } = useGettext();

const ITEMS_PER_PAGE = 25;
const SEARCH_DEBOUNCE_MILLISECONDS = 300;

const searchTerm = ref("");
const candidates = ref<SearchResultItem[]>([]);
const isLoading = ref(false);
const fetchError = ref<string | null>(null);
let debounceTimeout: ReturnType<typeof setTimeout> | undefined;

// Only a concept in Editing state can be retired after the merge, so the server
// rejects anything else. Filtering here keeps unusable candidates out of view.
const mergeableCandidates = computed(function () {
    return candidates.value.filter(
        (candidate) =>
            candidate.resource_instance_lifecycle_state_id ===
            EDITING_LIFECYCLE_STATE_ID,
    );
});

const hasFilteredOutCandidates = computed(function () {
    return candidates.value.length > mergeableCandidates.value.length;
});

async function fetchCandidates() {
    isLoading.value = true;
    fetchError.value = null;
    try {
        const parsedResponse = await fetchConceptResources(
            searchTerm.value,
            ITEMS_PER_PAGE,
            1,
            schemeId,
            [survivorConceptId],
        );
        candidates.value = parsedResponse.data;
    } catch (error) {
        fetchError.value =
            error instanceof Error ? error.message : String(error);
    } finally {
        isLoading.value = false;
    }
}

watch(searchTerm, function () {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(fetchCandidates, SEARCH_DEBOUNCE_MILLISECONDS);
});

onMounted(fetchCandidates);
</script>

<template>
    <div class="merge-picker">
        <IconField>
            <InputIcon
                :class="isLoading ? 'pi pi-spinner pi-spin' : 'pi pi-search'"
            />
            <InputText
                v-model="searchTerm"
                class="merge-picker-input"
                :placeholder="$gettext('Search concepts in this scheme')"
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
            v-if="isLoading && !mergeableCandidates.length"
            class="merge-picker-status"
        >
            {{ $gettext("Searching…") }}
        </p>

        <p
            v-else-if="!fetchError && !mergeableCandidates.length"
            class="merge-picker-status"
        >
            {{
                hasFilteredOutCandidates
                    ? $gettext(
                          "Every matching concept is outside the Editing state, so none can be merged away.",
                      )
                    : $gettext("No matching concepts in this scheme.")
            }}
        </p>

        <ul
            v-else-if="mergeableCandidates.length"
            class="merge-picker-results"
        >
            <li
                v-for="(candidate, index) in mergeableCandidates"
                :key="candidate.id"
            >
                <button
                    type="button"
                    class="merge-picker-result"
                    :class="{ selected: candidate.id === selectedConceptId }"
                    @click="emit('select', candidate)"
                >
                    <SearchResult
                        :search-result="{ index, option: candidate }"
                    />
                </button>
            </li>
        </ul>
    </div>
</template>

<style scoped>
/* The picker fills its step and scrolls its own list, so neither the number of
   results nor the length of a label changes the size of anything above it. */
.merge-picker {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    gap: 0.75rem;
}

/* Styled here rather than from the dialog: the class lands on the input itself,
   which a :deep() rule reaching in from the parent cannot match reliably. */
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

.merge-picker-result.selected :deep(.search-result) {
    background-color: var(--p-highlight-background);
    box-shadow: inset 0.1875rem 0 0 var(--p-primary-color);
}

.merge-picker-result:hover :deep(.search-result) {
    background-color: var(--p-search-result-focus-background);
}
</style>
