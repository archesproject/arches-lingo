<script setup lang="ts">
import { computed } from "vue";

import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Paginator from "primevue/paginator";
import ProgressSpinner from "primevue/progressspinner";
import SelectButton from "primevue/selectbutton";

import MatchCandidateRow from "@/arches_lingo/components/concept-matching/components/MatchCandidateRow.vue";

import {
    CANDIDATE_STATUS_DISMISSED,
    CANDIDATE_STATUS_LINKED,
    CANDIDATE_STATUS_MERGED,
    CANDIDATE_STATUS_PENDING,
    REVIEWABLE_CANDIDATE_STATUSES,
} from "@/arches_lingo/components/concept-matching/constants.ts";
import { SECONDARY } from "@/arches_lingo/constants.ts";

import type { ConceptMatchCandidate } from "@/arches_lingo/types.ts";

const {
    candidates,
    selectedIds,
    isLoading,
    totalResults,
    itemsPerPage,
    status,
    countsByStatus = {},
} = defineProps<{
    candidates: ConceptMatchCandidate[];
    selectedIds: Set<number>;
    isLoading: boolean;
    totalResults: number;
    itemsPerPage: number;
    firstResultIndex: number;
    status: string;
    countsByStatus?: Record<string, number>;
}>();

const emit = defineEmits<{
    (event: "update:selected", candidateId: number, isSelected: boolean): void;
    (event: "selectAllOnPage", isSelected: boolean): void;
    (event: "page", firstResultIndex: number): void;
    (event: "setStatus", newStatus: string): void;
    (event: "merge", candidateId: number): void;
}>();

const { $gettext } = useGettext();

const allOnPageSelected = () =>
    candidates.length > 0 &&
    candidates.every((candidate) => selectedIds.has(candidate.id));

// Linked and merged pairs are a record of what was done, not a queue: there is
// nothing left to decide about them, so they are read rather than worked on.
const isReviewable = computed(() =>
    REVIEWABLE_CANDIDATE_STATUSES.includes(status),
);

const statusOptions = computed(() => [
    {
        value: CANDIDATE_STATUS_PENDING,
        label: $gettext("To review (%{count})", {
            count: String(countsByStatus[CANDIDATE_STATUS_PENDING] ?? 0),
        }),
    },
    {
        value: CANDIDATE_STATUS_DISMISSED,
        label: $gettext("Dismissed (%{count})", {
            count: String(countsByStatus[CANDIDATE_STATUS_DISMISSED] ?? 0),
        }),
    },
    {
        value: CANDIDATE_STATUS_LINKED,
        label: $gettext("Linked (%{count})", {
            count: String(countsByStatus[CANDIDATE_STATUS_LINKED] ?? 0),
        }),
    },
    {
        value: CANDIDATE_STATUS_MERGED,
        label: $gettext("Merged (%{count})", {
            count: String(countsByStatus[CANDIDATE_STATUS_MERGED] ?? 0),
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
</script>

<template>
    <div class="candidate-list">
        <div class="candidate-list-toolbar">
            <Button
                v-if="isReviewable"
                :label="
                    allOnPageSelected()
                        ? $gettext('Clear selection')
                        : $gettext('Select all on page')
                "
                :severity="SECONDARY"
                :outlined="true"
                :disabled="!candidates.length"
                class="toolbar-button"
                @click="emit('selectAllOnPage', !allOnPageSelected())"
            />

            <SelectButton
                :model-value="status"
                :options="statusOptions"
                option-label="label"
                option-value="value"
                :allow-empty="false"
                class="status-filter"
                @update:model-value="emit('setStatus', $event)"
            />
        </div>

        <ProgressSpinner
            v-if="isLoading"
            class="candidate-spinner"
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
                @update:selected="
                    (candidateId, isSelected) =>
                        emit('update:selected', candidateId, isSelected)
                "
                @merge="emit('merge', $event)"
            />

            <Paginator
                :rows="itemsPerPage"
                :total-records="totalResults"
                :first="firstResultIndex"
                @page="emit('page', $event.first)"
            />
        </template>
    </div>
</template>

<style scoped>
.candidate-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    min-height: 0;
}

.candidate-list-toolbar {
    display: flex;
    gap: 0.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
}

.toolbar-button {
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
}

.candidate-spinner {
    align-self: center;
    width: 2.5rem;
    height: 2.5rem;
}

.candidate-empty {
    margin: 0;
    padding: 1rem 0;
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-light);
    color: var(--p-inputtext-placeholder-color);
}
</style>
