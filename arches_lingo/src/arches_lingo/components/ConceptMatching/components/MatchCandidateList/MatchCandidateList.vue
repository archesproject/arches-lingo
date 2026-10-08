<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Paginator from "primevue/paginator";
import ProgressSpinner from "primevue/progressspinner";
import SelectButton from "primevue/selectbutton";
import MatchCandidateRow from "@/arches_lingo/components/ConceptMatching/components/MatchCandidateList/components/MatchCandidateRow.vue";

import {
    CANDIDATE_STATUS_DISMISSED,
    CANDIDATE_STATUS_LINKED,
    CANDIDATE_STATUS_MERGED,
    CANDIDATE_STATUS_PENDING,
    REVIEWABLE_CANDIDATE_STATUSES,
    SEARCH_DEBOUNCE_MS,
} from "@/arches_lingo/components/ConceptMatching/constants.ts";
import { SECONDARY } from "@/arches_lingo/constants.ts";

import type { PageState } from "primevue/paginator";
import type {
    ConceptMatchCandidate,
    ConceptMatchCandidateStatus,
} from "@/arches_lingo/types.ts";
import type { CandidateSelectionChange } from "@/arches_lingo/components/ConceptMatching/types.ts";

const {
    candidates,
    selectedIds,
    isLoading,
    totalResults,
    itemsPerPage,
    pageNumber,
    status,
    countsByStatus,
    searchText,
} = defineProps<{
    candidates: ConceptMatchCandidate[];
    selectedIds: Set<number>;
    isLoading: boolean;
    totalResults: number;
    itemsPerPage: number;
    pageNumber: number;
    status: ConceptMatchCandidateStatus;
    countsByStatus: Record<ConceptMatchCandidateStatus, number>;
    searchText: string;
}>();

const emit = defineEmits<{
    (event: "selection-changed", payload: CandidateSelectionChange): void;
    (event: "select-all-on-page", payload: { isSelected: boolean }): void;
    (event: "page-changed", payload: { pageNumber: number }): void;
    (
        event: "status-changed",
        payload: { status: ConceptMatchCandidateStatus },
    ): void;
    (event: "merge-requested", payload: { candidateId: number }): void;
    (event: "search-changed", payload: { searchText: string }): void;
}>();

const { $gettext } = useGettext();

const draftSearchText = ref(searchText);

let searchTimer: ReturnType<typeof setTimeout> | undefined;

const allOnPageSelected = computed(
    () =>
        candidates.length > 0 &&
        candidates.every((candidate) => selectedIds.has(candidate.id)),
);

const isReviewable = computed(() =>
    REVIEWABLE_CANDIDATE_STATUSES.includes(status),
);

const firstResultIndex = computed(() => (pageNumber - 1) * itemsPerPage);

const statusOptions = computed(() => [
    {
        value: CANDIDATE_STATUS_PENDING,
        label: $gettext("To review (%{count})", {
            count: String(countsByStatus[CANDIDATE_STATUS_PENDING]),
        }),
    },
    {
        value: CANDIDATE_STATUS_DISMISSED,
        label: $gettext("Dismissed (%{count})", {
            count: String(countsByStatus[CANDIDATE_STATUS_DISMISSED]),
        }),
    },
    {
        value: CANDIDATE_STATUS_LINKED,
        label: $gettext("Linked (%{count})", {
            count: String(countsByStatus[CANDIDATE_STATUS_LINKED]),
        }),
    },
    {
        value: CANDIDATE_STATUS_MERGED,
        label: $gettext("Merged (%{count})", {
            count: String(countsByStatus[CANDIDATE_STATUS_MERGED]),
        }),
    },
]);

const emptyText = computed(function () {
    if (searchText) {
        return $gettext(
            'No pairs in this list have a label containing "%{search}".',
            {
                search: searchText,
            },
        );
    }
    switch (status) {
        case CANDIDATE_STATUS_DISMISSED:
            return $gettext("None of this run's pairs have been dismissed.");
        case CANDIDATE_STATUS_LINKED:
            return $gettext("None of this run's pairs have been linked.");
        case CANDIDATE_STATUS_MERGED:
            return $gettext("None of this run's pairs have been merged.");
        default:
            return $gettext("Nothing left to review in this run.");
    }
});

// Back and forward change the filter without the input, so it follows the route.
watch(
    () => searchText,
    function (routeSearchText) {
        draftSearchText.value = routeSearchText;
    },
);

watch(draftSearchText, function (typedSearchText) {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
        const trimmedSearchText = typedSearchText.trim();
        if (trimmedSearchText !== searchText) {
            emit("search-changed", { searchText: trimmedSearchText });
        }
    }, SEARCH_DEBOUNCE_MS);
});

onBeforeUnmount(() => clearTimeout(searchTimer));

function toggleSelectAllOnPage(): void {
    emit("select-all-on-page", { isSelected: !allOnPageSelected.value });
}

function onStatusChosen(chosenStatus: ConceptMatchCandidateStatus): void {
    emit("status-changed", { status: chosenStatus });
}

function onPageChosen(pageState: PageState): void {
    emit("page-changed", { pageNumber: pageState.page + 1 });
}
</script>

<template>
    <div class="candidate-list">
        <div class="candidate-list-toolbar">
            <Button
                v-if="isReviewable"
                class="toolbar-button"
                :label="
                    allOnPageSelected
                        ? $gettext('Clear selection')
                        : $gettext('Select all on page')
                "
                :severity="SECONDARY"
                :outlined="true"
                :disabled="!candidates.length"
                @click="toggleSelectAllOnPage"
            />

            <SelectButton
                class="status-filter"
                option-label="label"
                option-value="value"
                :model-value="status"
                :options="statusOptions"
                :allow-empty="false"
                :aria-label="$gettext('Show pairs')"
                @update:model-value="onStatusChosen"
            />

            <IconField class="label-filter">
                <InputIcon class="pi pi-search" />
                <InputText
                    v-model="draftSearchText"
                    class="label-filter-input"
                    type="search"
                    :placeholder="$gettext('Filter by label')"
                    :aria-label="$gettext('Filter pairs by label')"
                />
            </IconField>
        </div>

        <ProgressSpinner
            v-if="isLoading"
            class="candidate-spinner"
            :aria-label="$gettext('Loading pairs')"
        />

        <p
            v-else-if="!candidates.length"
            class="candidate-empty"
        >
            {{ emptyText }}
        </p>

        <template v-else>
            <MatchCandidateRow
                v-for="candidate in candidates"
                :key="candidate.id"
                :candidate="candidate"
                :is-selected="selectedIds.has(candidate.id)"
                :is-reviewable="isReviewable"
                @selection-changed="emit('selection-changed', $event)"
                @merge-requested="emit('merge-requested', $event)"
            />
        </template>

        <Paginator
            v-if="totalResults > 0"
            :rows="itemsPerPage"
            :total-records="totalResults"
            :first="firstResultIndex"
            @page="onPageChosen"
        />
    </div>
</template>

<style scoped>
.candidate-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    min-height: 0;
}

.candidate-list .candidate-list-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    padding-block-end: 0.5rem;
    border-block-end: 0.0625rem solid var(--p-content-border-color);
}

.candidate-list .candidate-list-toolbar .label-filter {
    flex: 1 1 14rem;
    max-width: 22rem;
}

.candidate-list .candidate-list-toolbar .label-filter-input {
    width: 100%;
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
}

.candidate-list .candidate-list-toolbar .toolbar-button {
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
}

.candidate-list .candidate-spinner {
    align-self: center;
    width: 2.5rem;
    height: 2.5rem;
}

.candidate-list .candidate-empty {
    margin: 0;
    padding-block: 1rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-light);
    color: var(--p-text-muted-color);
}
</style>
