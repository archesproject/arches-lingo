<script setup lang="ts">
import {
    computed,
    nextTick,
    onMounted,
    onUnmounted,
    ref,
    useId,
    useTemplateRef,
    watch,
} from "vue";
import { useGettext } from "vue3-gettext";
import { useRouter } from "vue-router";

import Button from "primevue/button";
import InputText from "primevue/inputtext";
import ProgressBar from "primevue/progressbar";
import { useToast } from "primevue/usetoast";

import SortAndFilterControls from "@/arches_lingo/components/basic-search/SortAndFilterControls.vue";
import SearchResult from "@/arches_lingo/components/basic-search/SearchResult.vue";

import { fetchSearchResults } from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";
import { scaleWithRootFontSize } from "@/arches_lingo/utils.ts";
import { useLocalAnnouncer } from "@/arches_lingo/composables/useAnnouncer.ts";
import { useRovingListFocus } from "@/arches_lingo/composables/useRovingListFocus.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import type { SearchResultItem } from "@/arches_lingo/types.ts";

interface Props {
    searchResultsPerPage: number;
    resultsDisplay?: "inline" | "floating";
}

const props = withDefaults(defineProps<Props>(), {
    resultsDisplay: "inline",
});

const emit = defineEmits<{ select: [] }>();

const SEARCH_DELAY_MS = 500;
// VoiceOver drops a status message sent while it is still echoing typing.
const RESULTS_ANNOUNCEMENT_DELAY_MS = 750;
const LOAD_MORE_SCROLL_THRESHOLD = scaleWithRootFontSize(64);

const { $gettext, $ngettext } = useGettext();
const { localMessage, announceLocally } = useLocalAnnouncer();
const router = useRouter();
const toast = useToast();

const rootRef = useTemplateRef<HTMLElement>("root");
const resultsList = useTemplateRef<HTMLUListElement>("resultsList");
const resultsListId = useId();

const query = ref("");
const orderMode = ref("unsorted");
const searchResults = ref<SearchResultItem[]>([]);
const searchResultsPage = ref(1);
const searchResultsTotalCount = ref(0);
const searchResultsTotalPages = ref(0);
const resultsMaxHeight = ref("60vh");
const isLoading = ref(false);
const isLoadingAdditionalResults = ref(false);
const hasSearchResponse = ref(false);
const isResultsPanelOpen = ref(false);

let searchDelayTimeoutId: number | undefined;
let resultsAnnouncementTimeoutId: number | undefined;

const { focusItem: focusResultLink, onListKeydown: onArrowKeyInResults } =
    useRovingListFocus(getResultLinks);

const isFloatingResults = computed(() => props.resultsDisplay === "floating");

const resultsHostClass = computed(() => {
    if (isFloatingResults.value) {
        return "results-host results-host--floating";
    }

    return "results-host results-host--inline";
});

const isResultsPanelVisible = computed(
    () =>
        isResultsPanelOpen.value &&
        Boolean(query.value) &&
        hasSearchResponse.value,
);

const hasMoreResults = computed(
    () => searchResultsPage.value < searchResultsTotalPages.value,
);

function getResultLinks() {
    return [
        ...(resultsList.value?.querySelectorAll<HTMLElement>(".result-link") ??
            []),
    ];
}

function getLastResultsPanelFocusable() {
    const panelFocusables =
        rootRef.value?.querySelectorAll<HTMLElement>(
            ".result-link, .load-more-button",
        ) ?? [];
    return panelFocusables[panelFocusables.length - 1];
}

function getResultPositionDescription(resultIndex: number) {
    return $gettext("Result %{position} of %{total}", {
        position: String(resultIndex + 1),
        total: String(searchResultsTotalCount.value),
    });
}

function getInputElement() {
    return rootRef.value?.querySelector<HTMLInputElement>(".search-input");
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

function openResultsPanel() {
    updateResultsMaxHeight();
    isResultsPanelOpen.value = true;
}

function closeResultsPanel() {
    isResultsPanelOpen.value = false;
}

function resetSearchResults() {
    searchResults.value = [];
    searchResultsPage.value = 1;
    searchResultsTotalCount.value = 0;
    searchResultsTotalPages.value = 0;
    hasSearchResponse.value = false;
}

function clearInput() {
    query.value = "";
    focusInput();
}

function updateResultsMaxHeight() {
    const rootFontSize = parseFloat(
        getComputedStyle(document.documentElement).fontSize,
    );
    let maxHeight = window.innerHeight * 0.6;

    if (isFloatingResults.value && rootRef.value) {
        maxHeight = Math.max(
            window.innerHeight -
                rootRef.value.getBoundingClientRect().bottom -
                rootFontSize * 2,
            rootFontSize * 5,
        );
    }

    resultsMaxHeight.value = `${maxHeight}px`;
}

async function fetchData(searchTerm: string, pageNumber: number) {
    const searchOrderMode = orderMode.value;
    isLoading.value = true;
    isLoadingAdditionalResults.value = pageNumber > 1;

    try {
        const parsedResponse = await fetchSearchResults(
            searchTerm,
            props.searchResultsPerPage,
            pageNumber,
            searchOrderMode,
        );

        if (searchTerm !== query.value || searchOrderMode !== orderMode.value) {
            return;
        }

        if (pageNumber === 1) {
            searchResults.value = parsedResponse.data;
            openResultsPanel();
        } else {
            searchResults.value = [
                ...searchResults.value,
                ...parsedResponse.data,
            ];
        }
        searchResultsPage.value = parsedResponse.current_page;
        searchResultsTotalCount.value = parsedResponse.total_results;
        searchResultsTotalPages.value = parsedResponse.total_pages;
        hasSearchResponse.value = true;
        announceSearchResults(pageNumber);
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to fetch data."),
            detail: error instanceof Error ? error.message : undefined,
        });

        resetSearchResults();
    } finally {
        isLoading.value = false;
        isLoadingAdditionalResults.value = false;
    }
}

function queueResultsAnnouncement(message: string) {
    window.clearTimeout(resultsAnnouncementTimeoutId);
    resultsAnnouncementTimeoutId = window.setTimeout(() => {
        void announceLocally(message);
    }, RESULTS_ANNOUNCEMENT_DELAY_MS);
}

function announceSearchResults(pageNumber: number) {
    const totalCount = searchResultsTotalCount.value;
    if (!totalCount) {
        queueResultsAnnouncement($gettext("No results found."));
    } else if (pageNumber === 1) {
        queueResultsAnnouncement(
            $ngettext(
                "%{count} result found",
                "%{count} results found",
                totalCount,
                { count: String(totalCount) },
            ),
        );
    } else {
        queueResultsAnnouncement(
            $gettext("Showing %{shown} of %{total} results", {
                shown: String(searchResults.value.length),
                total: String(totalCount),
            }),
        );
    }
}

async function loadMoreResults() {
    if (isLoading.value || !hasMoreResults.value) {
        return;
    }

    await fetchData(query.value, searchResultsPage.value + 1);
}

function loadMoreIfScrolledToEnd() {
    const list = resultsList.value;
    if (!list || !hasMoreResults.value) {
        return;
    }

    const distanceToEnd =
        list.scrollHeight - list.scrollTop - list.clientHeight;
    if (distanceToEnd <= LOAD_MORE_SCROLL_THRESHOLD) {
        void loadMoreResults();
    }
}

async function loadMoreResultsAndFocusFirstNew() {
    const firstNewResultIndex = searchResults.value.length;
    await loadMoreResults();

    if (searchResults.value.length > firstNewResultIndex) {
        await nextTick();
        focusResultLink(firstNewResultIndex);
    }
}

function onSearchKeydown(event: KeyboardEvent) {
    if (!isResultsPanelVisible.value) {
        return;
    }

    const isTabFromLastResult =
        event.key === "Tab" &&
        !event.shiftKey &&
        event.target === getLastResultsPanelFocusable();

    if (event.key === "Escape") {
        event.stopPropagation();
        closeResultsPanel();
    } else if (!isTabFromLastResult) {
        return;
    }

    event.preventDefault();
    focusInput();
}

function onInputKeydown(event: KeyboardEvent) {
    if (event.key !== "ArrowDown" || !searchResults.value.length) {
        return;
    }

    event.preventDefault();
    openResultsPanel();
    nextTick(() => focusResultLink(0));
}

function onResultsKeydown(event: KeyboardEvent) {
    if (event.key === "ArrowUp" && event.target === getResultLinks()[0]) {
        event.preventDefault();
        focusInput();
        return;
    }

    onArrowKeyInResults(event);
}

function onSearchFocusOut(event: FocusEvent) {
    if (event.relatedTarget && !isInsideSearch(event.relatedTarget)) {
        closeResultsPanel();
    }
}

function onDocumentPointerDown(event: PointerEvent) {
    if (!isInsideSearch(event.target)) {
        closeResultsPanel();
    }
}

function onInputClick() {
    if (hasSearchResponse.value) {
        openResultsPanel();
    }
}

async function openSearchResult(
    clickEvent: MouseEvent,
    searchResult: SearchResultItem,
) {
    const isOpeningElsewhere =
        clickEvent.button !== 0 ||
        clickEvent.metaKey ||
        clickEvent.ctrlKey ||
        clickEvent.shiftKey ||
        clickEvent.altKey;
    if (isOpeningElsewhere) {
        return;
    }

    clickEvent.preventDefault();
    const failure = await router.push({
        name: routeNames.concept,
        params: { id: searchResult.id },
    });

    if (!failure) {
        query.value = "";
        emit("select");
    }
}

onMounted(() => {
    focusInput();
    document.addEventListener("pointerdown", onDocumentPointerDown);
    window.addEventListener("resize", updateResultsMaxHeight);
});

onUnmounted(() => {
    document.removeEventListener("pointerdown", onDocumentPointerDown);
    window.removeEventListener("resize", updateResultsMaxHeight);
    window.clearTimeout(searchDelayTimeoutId);
    window.clearTimeout(resultsAnnouncementTimeoutId);
});

watch(query, (newQuery) => {
    window.clearTimeout(searchDelayTimeoutId);

    if (!newQuery) {
        resetSearchResults();
        return;
    }

    searchDelayTimeoutId = window.setTimeout(() => {
        void fetchData(newQuery, 1);
    }, SEARCH_DELAY_MS);
});

watch(orderMode, (newOrderMode, previousOrderMode) => {
    if (!query.value || newOrderMode === previousOrderMode) {
        return;
    }

    void fetchData(query.value, 1);
});
</script>

<template>
    <div
        ref="root"
        class="basic-search"
        @keydown="onSearchKeydown"
        @focusout="onSearchFocusOut"
    >
        <div class="search-input-row">
            <i
                class="pi pi-search search-icon"
                aria-hidden="true"
            />

            <InputText
                v-model="query"
                class="search-input"
                role="searchbox"
                autocomplete="off"
                :placeholder="$gettext('Quick Search')"
                :aria-label="$gettext('Quick Search')"
                :aria-controls="
                    isResultsPanelVisible ? resultsListId : undefined
                "
                @keydown="onInputKeydown"
                @click="onInputClick"
            />

            <Button
                v-if="query"
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
                :aria-label="$gettext('Searching')"
            />
        </div>

        <div
            v-if="isResultsPanelVisible"
            :class="resultsHostClass"
        >
            <p
                v-if="!searchResults.length"
                class="no-results"
            >
                {{ $gettext("No search results found") }}
            </p>

            <ul
                v-else
                :id="resultsListId"
                ref="resultsList"
                class="results-list"
                :aria-label="$gettext('Search results')"
                :style="{ maxHeight: resultsMaxHeight }"
                @scroll="loadMoreIfScrolledToEnd"
                @keydown="onResultsKeydown"
            >
                <li
                    v-for="(searchResult, resultIndex) in searchResults"
                    :key="searchResult.id"
                >
                    <SearchResult
                        :search-result="{
                            index: resultIndex,
                            option: searchResult,
                        }"
                        is-link
                        :position-description="
                            getResultPositionDescription(resultIndex)
                        "
                        @select="
                            (clickEvent) =>
                                openSearchResult(clickEvent, searchResult)
                        "
                    />
                </li>
            </ul>

            <ProgressBar
                v-if="isLoadingAdditionalResults"
                mode="indeterminate"
                style="height: 0.5rem"
                :aria-label="$gettext('Loading more results')"
            />

            <Button
                v-if="hasMoreResults"
                class="load-more-button"
                :loading="isLoadingAdditionalResults"
                size="small"
                text
                :label="
                    $gettext('Load more results (%{shown} of %{total})', {
                        shown: String(searchResults.length),
                        total: String(searchResultsTotalCount),
                    })
                "
                @click="loadMoreResultsAndFocusFirstNew"
            />
        </div>

        <div
            role="status"
            class="p-hidden-accessible"
        >
            {{ localMessage }}
        </div>
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

.search-input {
    width: 100%;
    padding: 1rem 2.5rem;
    border: 0.0625rem solid var(--p-header-button-border);
    border-radius: 0.25rem;
    margin-bottom: 0.25rem;
}

:deep(.p-progressbar .p-progressbar-value) {
    background: var(--p-primary-800);
}

.results-host {
    background-color: var(--p-dialog-background);
    border-top: 0.0725rem solid var(--p-dialog-border-color);
}

.results-list {
    margin: 0;
    padding: 0;
    list-style: none;
    overflow-y: auto;
}

.no-results {
    margin: 0;
    padding: 0.5rem;
    text-align: center;
}

.load-more-button:not(:focus-visible) {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: -1px;
    padding: 0;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
    border: 0;
}

.load-more-button:focus-visible {
    width: 100%;
}

.results-host--floating {
    position: absolute;
    inset-inline: 0;
    inset-block-start: 100%;
    z-index: 10;
}
</style>
