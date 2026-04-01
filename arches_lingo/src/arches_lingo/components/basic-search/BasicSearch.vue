<script setup lang="ts">
import {
    computed,
    nextTick,
    onMounted,
    onUnmounted,
    ref,
    useTemplateRef,
    watch,
} from "vue";
import { useGettext } from "vue3-gettext";
import { useRouter } from "vue-router";

import AutoComplete from "primevue/autocomplete";
import Button from "primevue/button";
import ProgressBar from "primevue/progressbar";
import { useToast } from "primevue/usetoast";

import SortAndFilterControls from "@/arches_lingo/components/basic-search/SortAndFilterControls.vue";
import SearchResult from "@/arches_lingo/components/basic-search/SearchResult.vue";

import { fetchSearchResults } from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import type { AutoCompleteOptionSelectEvent } from "primevue/autocomplete";
import type { VirtualScrollerLazyEvent } from "primevue/virtualscroller";
import type { SearchResultItem } from "@/arches_lingo/types.ts";

interface Props {
    searchResultsPerPage: number;
    searchResultItemSize: number;
    resultsDisplay?: "inline" | "floating";
}

const props = withDefaults(defineProps<Props>(), {
    resultsDisplay: "inline",
});

const emit = defineEmits<{ select: [] }>();

const { $gettext } = useGettext();
const router = useRouter();
const toast = useToast();

const autoCompleteRef = useTemplateRef("autoComplete");
const rootRef = useTemplateRef<HTMLElement>("root");
const resultsHostRef = useTemplateRef<HTMLElement>("resultsHost");

const autoCompleteKey = ref(0);
const query = ref("");
const orderMode = ref("unsorted");
const searchResults = ref<SearchResultItem[]>([]);
const searchResultsPage = ref(1);
const searchResultsTotalCount = ref(0);
const searchResultsHeight = ref("2.25rem");
const isLoading = ref(false);
const isLoadingAdditionalResults = ref(false);
const shouldShowClearInputButton = ref(false);

const isFloatingResults = computed(() => props.resultsDisplay === "floating");

const resultsHostClass = computed(() => {
    if (isFloatingResults.value) {
        return "results-host results-host--floating";
    }

    return "results-host results-host--inline";
});

const autoCompleteAppendTarget = computed(() => resultsHostRef.value ?? "self");

const autoCompletePt = computed(() => ({
    option: {
        style: {
            padding: "0",
            borderRadius: "0",
        },
    },
    overlay: {
        class: "basic-search-overlay",
        style: {
            padding: "0",
            borderRadius: "0",
            borderTop: "0.0725rem solid var(--p-dialog-border-color)",
        },
    },
    list: {
        style: {
            padding: "0",
            gap: "0",
        },
    },
}));

function getInputElement() {
    // @ts-expect-error - PrimeVue component instance typing is incomplete
    const input = autoCompleteRef.value?.$el?.querySelector("input");
    return input instanceof HTMLInputElement ? input : null;
}

function isInsideSearch(eventTarget: EventTarget | null) {
    return (
        eventTarget instanceof Node &&
        Boolean(rootRef.value?.contains(eventTarget))
    );
}

function focusInput() {
    getInputElement()?.focus();
}

function showOverlay() {
    updateLayoutMetrics();
    // @ts-expect-error - PrimeVue component instance typing is incomplete
    autoCompleteRef.value?.show();
}

function hideOverlay() {
    // @ts-expect-error - PrimeVue component instance typing is incomplete
    autoCompleteRef.value?.hide();
}

function resetSearchResults() {
    searchResults.value = [];
    searchResultsPage.value = 1;
    searchResultsTotalCount.value = 0;
}

function clearInput() {
    query.value = "";
    shouldShowClearInputButton.value = false;
    resetSearchResults();
    hideOverlay();
    focusInput();
}

function getSearchResultsHeight(results: SearchResultItem[]) {
    if (!results.length) {
        return "2.25rem";
    }

    const rootFontSize = parseFloat(
        getComputedStyle(document.documentElement).fontSize,
    );
    const totalHeightInRem =
        results.length * (props.searchResultItemSize / rootFontSize);

    let maxHeightInRem = (window.innerHeight * 0.6) / rootFontSize;

    if (isFloatingResults.value && rootRef.value) {
        maxHeightInRem = Math.max(
            (window.innerHeight -
                rootRef.value.getBoundingClientRect().bottom -
                rootFontSize * 2) /
                rootFontSize,
            5,
        );
    }

    return `${Math.min(totalHeightInRem, maxHeightInRem)}rem`;
}

function updateLayoutMetrics() {
    searchResultsHeight.value = getSearchResultsHeight(searchResults.value);
}

async function fetchData(
    searchTerm: string,
    items: number,
    pageNumber: number,
    orderModeValue: string,
) {
    isLoading.value = true;
    shouldShowClearInputButton.value = pageNumber !== 1;

    try {
        const parsedResponse = await fetchSearchResults(
            searchTerm,
            items,
            pageNumber,
            orderModeValue,
        );

        if (searchTerm !== query.value) {
            return;
        }

        if (!query.value) {
            resetSearchResults();
            return;
        }

        if (pageNumber === 1) {
            searchResults.value = parsedResponse.data;
        } else {
            searchResults.value = [
                ...searchResults.value,
                ...parsedResponse.data,
            ];
        }
        searchResultsPage.value = parsedResponse.current_page;
        searchResultsTotalCount.value = parsedResponse.total_results;
        shouldShowClearInputButton.value = true;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to fetch data."),
            detail: error instanceof Error ? error.message : undefined,
        });

        resetSearchResults();
        shouldShowClearInputButton.value = true;
    } finally {
        isLoading.value = false;
        isLoadingAdditionalResults.value = false;
    }
}

function onDocumentPointerDown(event: PointerEvent) {
    if (!isInsideSearch(event.target)) {
        hideOverlay();
    }
}

function keepOverlayVisible() {
    if (!query.value || !searchResults.value.length) {
        return;
    }

    if (isLoading.value !== isLoadingAdditionalResults.value) {
        return;
    }

    nextTick(() => {
        if (isInsideSearch(document.activeElement)) {
            showOverlay();
        }
    });
}

function onComplete() {
    hideOverlay();
    void fetchData(query.value, props.searchResultsPerPage, 1, orderMode.value);
}

function loadAdditionalSearchResults(event: VirtualScrollerLazyEvent) {
    if (
        event.last < searchResultsPage.value * props.searchResultsPerPage ||
        event.last > searchResultsTotalCount.value
    ) {
        return;
    }

    isLoadingAdditionalResults.value = true;
    searchResultsPage.value += 1;

    void fetchData(
        query.value,
        props.searchResultsPerPage,
        searchResultsPage.value,
        orderMode.value,
    );
}

async function navigateToReport(event: AutoCompleteOptionSelectEvent) {
    const failure = await router.push({
        name: routeNames.concept,
        params: { id: event.value.id },
    });

    if (!failure) {
        emit("select");
    }
}

onMounted(() => {
    focusInput();
    updateLayoutMetrics();
    document.addEventListener("pointerdown", onDocumentPointerDown);
    window.addEventListener("resize", updateLayoutMetrics);
});

onUnmounted(() => {
    document.removeEventListener("pointerdown", onDocumentPointerDown);
    window.removeEventListener("resize", updateLayoutMetrics);
});

watch(query, (newQueryValue) => {
    if (newQueryValue) {
        return;
    }

    autoCompleteKey.value += 1;

    nextTick(() => {
        focusInput();
    });
});

watch(orderMode, async (newOrderMode, previousOrderMode) => {
    if (!query.value || newOrderMode === previousOrderMode) {
        return;
    }

    searchResultsPage.value = 1;

    await fetchData(query.value, props.searchResultsPerPage, 1, newOrderMode);

    if (searchResults.value.length) {
        nextTick(() => {
            showOverlay();
        });
    }
});

watch(searchResults, () => {
    updateLayoutMetrics();
});
</script>

<template>
    <div
        ref="root"
        class="basic-search"
    >
        <div class="search-input-row">
            <i
                class="pi pi-search search-icon"
                aria-hidden="true"
            />

            <AutoComplete
                ref="autoComplete"
                :key="autoCompleteKey"
                v-model="query"
                option-label="id"
                :append-to="autoCompleteAppendTarget"
                :delay="500"
                :loading="isLoading && !isLoadingAdditionalResults"
                :placeholder="$gettext('Quick Search')"
                :pt="autoCompletePt"
                :suggestions="searchResults"
                :virtual-scroller-options="{
                    itemSize: props.searchResultItemSize,
                    lazy: true,
                    onLazyLoad: loadAdditionalSearchResults,
                    scrollHeight: searchResultsHeight,
                    style: {
                        minHeight: searchResultsHeight,
                        maxHeight: searchResultsHeight,
                    },
                    numToleratedItems: 1,
                }"
                @complete="onComplete"
                @option-select="navigateToReport"
                @before-hide="keepOverlayVisible"
                @update:model-value="
                    (value) => {
                        if (!value) {
                            shouldShowClearInputButton = false;
                        }
                    }
                "
            >
                <template #empty>
                    <div style="text-align: center">
                        {{ $gettext("No search results found") }}
                    </div>
                </template>

                <template #option="slotProps">
                    <SearchResult :search-result="slotProps" />
                </template>

                <template
                    v-if="isLoadingAdditionalResults"
                    #footer
                >
                    <ProgressBar
                        mode="indeterminate"
                        style="height: 0.5rem"
                    />
                </template>
            </AutoComplete>

            <Button
                v-if="shouldShowClearInputButton"
                class="p-button-text clear-button"
                icon="pi pi-times"
                :aria-label="$gettext('Clear Input')"
                @click="clearInput"
            />
        </div>

        <div class="controls-container">
            <SortAndFilterControls v-model:order-mode="orderMode" />

            <ProgressBar
                v-if="isLoading && !isLoadingAdditionalResults"
                mode="indeterminate"
                style="height: 0.25rem"
            />
        </div>

        <div
            ref="resultsHost"
            :class="resultsHostClass"
        />
    </div>
</template>

<style scoped>
.basic-search {
    width: 100%;
    font-family: var(--p-lingo-font-family);
    padding: 0.25rem;
    position: relative;
}

.search-input-row {
    display: flex;
    align-items: center;
    position: relative;
}

.controls-container,
.results-host {
    width: 100%;
}

.clear-button {
    background-color: transparent !important;
    position: absolute;
    inset-inline-end: 0.2rem;
    color: var(--p-input-color);
}

.search-icon {
    position: absolute;
    inset-inline-start: 1rem;
    z-index: 1;
    font-weight: bold;
}

.p-autocomplete {
    width: 100%;
    border: 0.0625rem solid var(--p-header-button-border);
    border-radius: 0.25rem;
    margin-bottom: 0.25rem;
}

:deep(.p-autocomplete-loader) {
    color: var(--p-primary-600);
}

:deep(.p-progressbar .p-progressbar-value) {
    background: var(--p-primary-800);
}

:deep(.p-autocomplete .p-autocomplete-input) {
    width: 100%;
    padding: 1rem 2.5rem;
    border: none;
}

:deep(.p-autocomplete-overlay) {
    border-top: 0.0725rem solid var(--p-dialog-border-color);
}

:deep(.basic-search-overlay) {
    position: static !important;
    inset: auto !important;
    width: 100% !important;
    margin-top: 0 !important;
}

.results-host--floating {
    position: absolute;
    inset-inline: 0;
    inset-block-start: 100%;
    z-index: 10;
}
</style>
