<script setup lang="ts">
import { nextTick, ref, watch, onMounted, useTemplateRef } from "vue";
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

const { $gettext } = useGettext();
const router = useRouter();
const toast = useToast();

interface Props {
    searchResultsPerPage: number;
    searchResultItemSize: number;
    toggleModal: () => void;
}
const props = defineProps<Props>();

const autoCompleteInstance = useTemplateRef("autoCompleteInstance");
const autoCompleteKey = ref(0);
const computedSearchResultsHeight = ref("");
const isLoading = ref(false);
const isLoadingAdditionalResults = ref(false);
const searchResults = ref<SearchResultItem[]>([]);
const searchResultsPage = ref(1);
const searchResultsTotalCount = ref(0);
const query = ref("");
const shouldShowClearInputButton = ref(false);

const clearInput = () => {
    query.value = "";
    shouldShowClearInputButton.value = false;
    focusInput();
};

const fetchData = async (searchTerm: string, items: number, page: number) => {
    isLoading.value = true;
    shouldShowClearInputButton.value = Boolean(page !== 1);

    try {
        const parsedResponse = await fetchSearchResults(
            searchTerm,
            items,
            page,
        );

        // This handles for when the user types a query and then
        // changes it before the request is completed.
        if (searchTerm !== query.value) {
            return;
        }

        if (query.value) {
            if (page === 1) {
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
        }
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to fetch data."),
            detail: error instanceof Error ? error.message : undefined,
        });

        searchResults.value = [];
        searchResultsPage.value = 1;
        searchResultsTotalCount.value = 0;
        shouldShowClearInputButton.value = true;
    } finally {
        isLoading.value = false;
        isLoadingAdditionalResults.value = false;
    }
};

const focusInput = () => {
    if (autoCompleteInstance.value) {
        // @ts-expect-error - autoCompleteInstance is mistyped in PrimeVue
        autoCompleteInstance.value.$el.querySelector("input").focus();
    }
};

const keepOverlayVisible = () => {
    if (
        query.value &&
        searchResults.value.length &&
        isLoading.value === isLoadingAdditionalResults.value
    ) {
        // @ts-expect-error - autoCompleteInstance is mistyped in PrimeVue
        nextTick(() => autoCompleteInstance.value?.show());
    }
};

const loadAdditionalSearchResults = (event: VirtualScrollerLazyEvent) => {
    if (
        event.last >= searchResultsPage.value * props.searchResultsPerPage &&
        event.last <= searchResultsTotalCount.value
    ) {
        isLoadingAdditionalResults.value = true;
        searchResultsPage.value += 1;

        fetchData(
            query.value,
            props.searchResultsPerPage,
            searchResultsPage.value,
        );
    }
};

const navigateToReport = async (event: AutoCompleteOptionSelectEvent) => {
    props.toggleModal();

    router.push({
        name: routeNames.concept,
        params: { id: event.value.id },
    });
};

onMounted(focusInput);

// handles the edge case of inputting a query then clearing the input before the data is fetched.
watch(query, (query) => {
    if (!query) {
        autoCompleteKey.value += 1;
        nextTick(() => {
            focusInput();
        });
    }
});

/**
 * This isn't fantastic but it's the best way I can find to get around PrimeVue's lack of support for
 * updating the height of a `VirtualScroller` overlay, much less updating the height dynamically.
 */
watch(searchResults, (searchResults) => {
    if (searchResults?.length) {
        const rootFontSize = parseFloat(
            getComputedStyle(document.documentElement).fontSize,
        );
        const itemHeightInRem = props.searchResultItemSize / rootFontSize; // Convert to rem based on the root font size
        const computedHeightInRem = searchResults.length * itemHeightInRem;

        const viewHeightInPixels = window.innerHeight * 0.6;
        const viewHeightInRem = viewHeightInPixels / rootFontSize; // Convert 60vh to rem

        if (computedHeightInRem > viewHeightInRem) {
            computedSearchResultsHeight.value = "60vh";
        } else {
            computedSearchResultsHeight.value = `${computedHeightInRem}rem`;
        }
    } else {
        computedSearchResultsHeight.value = "2.25rem";
    }
});
</script>

<template>
    <div id="basic-search-container">
        <div style="display: flex; align-items: center">
            <i
                class="pi pi-search search-icon"
                aria-hidden="true"
            />

            <AutoComplete
                ref="autoCompleteInstance"
                :key="autoCompleteKey"
                v-model="query"
                option-label="id"
                append-to="#basic-search-container"
                :delay="500"
                :loading="isLoading && !isLoadingAdditionalResults"
                :placeholder="$gettext('Quick Search')"
                :pt="{
                    option: {
                        style: {
                            padding: '0',
                            borderRadius: '0',
                        },
                    },
                    overlay: {
                        style: {
                            padding: '0',
                            borderRadius: '0',
                        },
                    },
                    list: {
                        style: {
                            padding: '0',
                            gap: '0',
                        },
                    },
                }"
                :suggestions="searchResults"
                :virtual-scroller-options="{
                    itemSize: props.searchResultItemSize,
                    lazy: true,
                    onLazyLoad: loadAdditionalSearchResults,
                    scrollHeight: computedSearchResultsHeight,
                    style: {
                        minHeight: computedSearchResultsHeight,
                        maxHeight: computedSearchResultsHeight,
                    },
                    numToleratedItems: 1,
                }"
                @complete="
                    () => {
                        // @ts-expect-error - autoCompleteInstance is mistyped in PrimeVue
                        autoCompleteInstance?.hide();
                        fetchData(query, props.searchResultsPerPage, 1);
                    }
                "
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

        <ProgressBar
            v-if="isLoading && !isLoadingAdditionalResults"
            mode="indeterminate"
            style="height: 0.25rem"
        />
        <SortAndFilterControls />
    </div>
</template>

<style scoped>
#basic-search-container {
    width: 100%;
    font-family: var(--p-lingo-font-family);
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
    position: static !important;
    border-top: 0.0725rem solid var(--p-dialog-border-color);
}
</style>
