<script setup lang="ts">
import { computed } from "vue";

import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
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
} from "@/arches_lingo/components/ConceptMatching/constants.ts";
import { SECONDARY } from "@/arches_lingo/constants.ts";

import type { PageState } from "primevue/paginator";
import type {
    ConceptMatchCandidate,
    ConceptMatchCandidateStatus,
} from "@/arches_lingo/types.ts";
import type { CandidateSelectionChange } from "@/arches_lingo/components/ConceptMatching/types.ts";

const SELECTION_CHANGED_EVENT = "selection-changed" as const;
const SELECT_ALL_ON_PAGE_EVENT = "select-all-on-page" as const;
const PAGE_CHANGED_EVENT = "page-changed" as const;
const STATUS_CHANGED_EVENT = "status-changed" as const;
const MERGE_REQUESTED_EVENT = "merge-requested" as const;

const {
    candidates,
    selectedIds,
    isLoading,
    totalResults,
    itemsPerPage,
    pageNumber,
    status,
    countsByStatus,
} = defineProps<{
    candidates: ConceptMatchCandidate[];
    selectedIds: Set<number>;
    isLoading: boolean;
    totalResults: number;
    itemsPerPage: number;
    pageNumber: number;
    status: ConceptMatchCandidateStatus;
    countsByStatus: Record<ConceptMatchCandidateStatus, number>;
}>();

const emit = defineEmits<{
    (
        event: typeof SELECTION_CHANGED_EVENT,
        payload: CandidateSelectionChange,
    ): void;
    (
        event: typeof SELECT_ALL_ON_PAGE_EVENT,
        payload: { isSelected: boolean },
    ): void;
    (event: typeof PAGE_CHANGED_EVENT, payload: { pageNumber: number }): void;
    (
        event: typeof STATUS_CHANGED_EVENT,
        payload: { status: ConceptMatchCandidateStatus },
    ): void;
    (
        event: typeof MERGE_REQUESTED_EVENT,
        payload: { candidateId: number },
    ): void;
}>();

const { $gettext } = useGettext();

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
    switch (status) {
        case CANDIDATE_STATUS_DISMISSED:
            return $gettext("Nothing has been dismissed in this run.");
        case CANDIDATE_STATUS_LINKED:
            return $gettext("Nothing has been linked from this run.");
        case CANDIDATE_STATUS_MERGED:
            return $gettext("Nothing has been merged from this run.");
        default:
            return $gettext("Nothing left to review in this run.");
    }
});

function toggleSelectAllOnPage(): void {
    emit(SELECT_ALL_ON_PAGE_EVENT, { isSelected: !allOnPageSelected.value });
}

function onStatusChosen(chosenStatus: ConceptMatchCandidateStatus): void {
    emit(STATUS_CHANGED_EVENT, { status: chosenStatus });
}

function onPageChosen(pageState: PageState): void {
    emit(PAGE_CHANGED_EVENT, { pageNumber: pageState.page + 1 });
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
                @selection-changed="emit(SELECTION_CHANGED_EVENT, $event)"
                @merge-requested="emit(MERGE_REQUESTED_EVENT, $event)"
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
    gap: 0.5rem;
    padding-block-end: 0.5rem;
    border-block-end: 0.0625rem solid var(--p-content-border-color);
}

.candidate-list-toolbar .toolbar-button {
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
