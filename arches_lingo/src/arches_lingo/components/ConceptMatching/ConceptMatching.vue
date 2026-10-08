<script setup lang="ts">
import { computed, inject, ref, watch } from "vue";

import { storeToRefs } from "pinia";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Message from "primevue/message";
import PanelToggleHeader from "@/arches_lingo/components/generic/PanelToggleHeader.vue";
import CandidateMergeFlow from "@/arches_lingo/components/ConceptMatching/components/CandidateMergeFlow/CandidateMergeFlow.vue";
import MatchCandidateList from "@/arches_lingo/components/ConceptMatching/components/MatchCandidateList/MatchCandidateList.vue";
import MatchReviewActions from "@/arches_lingo/components/ConceptMatching/components/MatchReviewActions.vue";
import MatchRunForm from "@/arches_lingo/components/ConceptMatching/components/MatchRunForm.vue";
import MatchRunProgress from "@/arches_lingo/components/ConceptMatching/components/MatchRunProgress.vue";
import MatchRunSelect from "@/arches_lingo/components/ConceptMatching/components/MatchRunSelect.vue";
import MatchRunSummary from "@/arches_lingo/components/ConceptMatching/components/MatchRunSummary.vue";

import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";
import { useCandidatePage } from "@/arches_lingo/components/ConceptMatching/composables/useCandidatePage.ts";
import { useConceptMatchRuns } from "@/arches_lingo/components/ConceptMatching/composables/useConceptMatchRuns.ts";
import { useErrorToast } from "@/arches_lingo/components/ConceptMatching/composables/useErrorToast.ts";
import { useMatchReviewRoute } from "@/arches_lingo/components/ConceptMatching/composables/useMatchReviewRoute.ts";
import {
    CANDIDATES_PER_PAGE,
    CANDIDATE_STATUS_DISMISSED,
    CANDIDATE_STATUS_PENDING,
} from "@/arches_lingo/components/ConceptMatching/constants.ts";
import { ERROR, INFO, SECONDARY, WARN } from "@/arches_lingo/constants.ts";

import type {
    ConceptMatchCandidate,
    ConceptMatchCandidateStatus,
    ConceptMatchRunRequest,
} from "@/arches_lingo/types.ts";

const refreshSchemeHierarchy = inject<() => void>("refreshSchemeHierarchy");

const { $gettext } = useGettext();
const conceptStore = useConceptStore();
const { user, isEditor } = storeToRefs(useUserStore());
const { reportError } = useErrorToast();

const {
    activeRunId,
    candidateStatus,
    pageNumber,
    searchText,
    conceptIdToSearchFrom,
    showView,
} = useMatchReviewRoute();

const {
    candidates,
    totalResults,
    isLoadingCandidates,
    loadError,
    hasUnshownResults,
    lastPageWhenPastEnd,
    selectedIds,
    loadCandidates,
    changeSelection,
    selectAllOnPage,
    clearSelection,
} = useCandidatePage({
    activeRunId,
    candidateStatus,
    pageNumber,
    searchText,
});

const {
    runs,
    activeRun,
    activeRunIsUnfinished,
    isCreatingRun,
    loadRuns,
    newestRunId,
    createRun,
} = useConceptMatchRuns({ activeRunId });

const showCriteria = ref(true);
const mergingCandidate = ref<ConceptMatchCandidate | null>(null);

const selectedCandidateIds = computed(() => Array.from(selectedIds.value));

// With a filter, the bulk actions cover only the filtered pairs, and the list's
// own total is exactly that count for the queue on screen.
const pendingCountInView = computed(() =>
    searchText.value ? totalResults.value : activeRun.value?.pending_count ?? 0,
);

const dismissedCountInView = computed(() =>
    searchText.value
        ? totalResults.value
        : activeRun.value?.counts_by_status[CANDIDATE_STATUS_DISMISSED] ?? 0,
);

const showNoRunsPrompt = computed(() => !activeRun.value && !runs.value.length);

watch(
    isEditor,
    function (userIsEditor) {
        if (userIsEditor) {
            initialize();
        }
    },
    { immediate: true },
);

// A page change keeps the selection, so pairs can be gathered across pages.
watch([candidateStatus, searchText], clearSelection);

watch([candidateStatus, pageNumber, searchText], () => loadCandidates());

watch(lastPageWhenPastEnd, function (lastPageNumber) {
    if (lastPageNumber !== null) {
        showView({ pageNumber: lastPageNumber }, { replace: true });
    }
});

// The first count is the one the initial load already shows.
watch(
    () => activeRun.value?.candidate_count,
    function (_candidateCount, previousCandidateCount) {
        if (
            previousCandidateCount !== undefined &&
            activeRunIsUnfinished.value
        ) {
            loadCandidates({ quiet: true });
        }
    },
);

// A deleted run also stops being unfinished.
watch(activeRunIsUnfinished, function (isUnfinished, wasUnfinished) {
    if (wasUnfinished && !isUnfinished && activeRun.value) {
        showFinishedResults();
    }
});

async function initialize(): Promise<void> {
    try {
        await conceptStore.initialize();
    } catch (error) {
        reportError(error, $gettext("Could not load schemes."));
    }

    await loadRuns();

    // Replacing the history entry keeps a reload from starting another run.
    const conceptId = conceptIdToSearchFrom();
    if (
        conceptId &&
        (await startRun({ source_concept_ids: [conceptId] }, { replace: true }))
    ) {
        return;
    }

    if (!(await showNewestRunIfNoneChosen())) {
        await loadCandidates();
    }
}

function showFinishedResults(): void {
    if (selectedIds.value.size) {
        hasUnshownResults.value = true;
        return;
    }
    loadCandidates();
}

async function showNewestRunIfNoneChosen(): Promise<boolean> {
    const runId = newestRunId();
    if (activeRunId !== null || runId === null) {
        return false;
    }
    await showView({ runId, pageNumber: 1, search: "" }, { replace: true });
    return true;
}

async function startRun(
    request: ConceptMatchRunRequest,
    { replace = false }: { replace?: boolean } = {},
): Promise<boolean> {
    const run = await createRun(request);
    if (!run) {
        return false;
    }
    await showView(
        {
            runId: run.id,
            pageNumber: 1,
            status: CANDIDATE_STATUS_PENDING,
            search: "",
        },
        { replace },
    );
    return true;
}

function onRunRequested(request: ConceptMatchRunRequest): void {
    startRun(request);
}

function onRunSelected({ runId }: { runId: number | null }): void {
    showView({ runId, pageNumber: 1, search: "" });
}

function onPageChanged({
    pageNumber: chosenPage,
}: {
    pageNumber: number;
}): void {
    showView({ pageNumber: chosenPage });
}

function onStatusChanged({
    status,
}: {
    status: ConceptMatchCandidateStatus;
}): void {
    showView({ pageNumber: 1, status });
}

// Replaces rather than pushes, so typing a filter doesn't fill the history.
function onSearchChanged({
    searchText: typedSearchText,
}: {
    searchText: string;
}): void {
    showView({ pageNumber: 1, search: typedSearchText }, { replace: true });
}

async function onReviewChanged(): Promise<void> {
    clearSelection();
    await Promise.all([loadRuns(), loadCandidates()]);
}

async function onRunDeleted(): Promise<void> {
    clearSelection();
    await loadRuns();
    await showView(
        {
            runId: newestRunId(),
            pageNumber: 1,
            status: CANDIDATE_STATUS_PENDING,
            search: "",
        },
        { replace: true },
    );
}

function onMergeRequested({ candidateId }: { candidateId: number }): void {
    mergingCandidate.value =
        candidates.value.find((candidate) => candidate.id === candidateId) ??
        null;
}

async function onMergeCompleted(): Promise<void> {
    if (mergingCandidate.value) {
        changeSelection({
            candidateId: mergingCandidate.value.id,
            isSelected: false,
        });
    }
    closeMerge();
    refreshSchemeHierarchy!();
    await Promise.all([loadRuns(), loadCandidates()]);
}

function closeMerge(): void {
    mergingCandidate.value = null;
}
</script>

<template>
    <div class="concept-matching">
        <PanelToggleHeader
            v-model:is-panel-visible="showCriteria"
            icon="pi pi-clone"
            hide-panel-icon="pi pi-angle-double-left"
            show-panel-icon="pi pi-sliders-h"
            :title="$gettext('Find Matching Concepts')"
            :hide-panel-label="$gettext('Hide Search Options')"
            :show-panel-label="$gettext('Show Search Options')"
            :can-toggle-panel="isEditor"
        />

        <Message
            v-if="user && !isEditor"
            class="access-message"
            :severity="WARN"
            :closable="false"
        >
            <span>{{
                $gettext(
                    "Finding matching concepts is available to Lingo editors.",
                )
            }}</span>
        </Message>

        <div
            v-if="isEditor"
            class="matches-body"
            :class="{ 'criteria-hidden': !showCriteria }"
        >
            <div
                v-show="showCriteria"
                class="matches-criteria"
            >
                <p class="intro">
                    {{
                        $gettext(
                            "Look for concepts that probably mean the same thing, then dismiss the ones that do not.",
                        )
                    }}
                </p>

                <MatchRunForm
                    :schemes="conceptStore.schemes"
                    :is-starting-run="isCreatingRun"
                    @run-requested="onRunRequested"
                />
            </div>

            <div class="matches-results">
                <div class="results-header">
                    <MatchRunSelect
                        :runs="runs"
                        :active-run-id="activeRunId"
                        @run-selected="onRunSelected"
                    />

                    <MatchReviewActions
                        v-if="activeRun"
                        :run-id="activeRun.id"
                        :candidate-status="candidateStatus"
                        :selected-candidate-ids="selectedCandidateIds"
                        :pending-count="pendingCountInView"
                        :dismissed-count="dismissedCountInView"
                        :search-text="searchText"
                        :candidate-count="activeRun.candidate_count"
                        :is-run-unfinished="activeRunIsUnfinished"
                        :can-delete-run="activeRun.can_delete"
                        @review-changed="onReviewChanged"
                        @run-deleted="onRunDeleted"
                    />
                </div>

                <MatchRunSummary
                    v-if="activeRun"
                    :run="activeRun"
                    :schemes="conceptStore.schemes"
                />

                <MatchRunProgress
                    v-if="activeRun && activeRunIsUnfinished"
                    :status="activeRun.status"
                    :candidate-count="activeRun.candidate_count"
                    :elapsed-seconds="activeRun.elapsed_seconds"
                />

                <Message
                    v-if="loadError"
                    :severity="ERROR"
                    :closable="false"
                >
                    <span>{{ loadError }}</span>
                </Message>

                <Message
                    v-if="hasUnshownResults"
                    :severity="INFO"
                    :closable="false"
                >
                    <span class="unshown-results">
                        <span>{{
                            $gettext(
                                "More pairs have been found. They appear once you refresh, so the list does not move while pairs are selected.",
                            )
                        }}</span>
                        <Button
                            size="small"
                            :label="$gettext('Show new results')"
                            :severity="SECONDARY"
                            :outlined="true"
                            @click="loadCandidates()"
                        />
                    </span>
                </Message>

                <p
                    v-if="showNoRunsPrompt"
                    class="no-runs"
                >
                    {{
                        $gettext(
                            "No searches yet. Choose what to compare, then select Find matches.",
                        )
                    }}
                </p>

                <MatchCandidateList
                    v-else-if="activeRun"
                    :candidates="candidates"
                    :selected-ids="selectedIds"
                    :is-loading="isLoadingCandidates"
                    :total-results="totalResults"
                    :items-per-page="CANDIDATES_PER_PAGE"
                    :page-number="pageNumber"
                    :status="candidateStatus"
                    :counts-by-status="activeRun.counts_by_status"
                    :search-text="searchText"
                    @selection-changed="changeSelection"
                    @select-all-on-page="selectAllOnPage($event.isSelected)"
                    @page-changed="onPageChanged"
                    @status-changed="onStatusChanged"
                    @search-changed="onSearchChanged"
                    @merge-requested="onMergeRequested"
                />
            </div>
        </div>

        <CandidateMergeFlow
            v-if="mergingCandidate?.concept_a && mergingCandidate.concept_b"
            :concept-a="mergingCandidate.concept_a"
            :concept-b="mergingCandidate.concept_b"
            @merged="onMergeCompleted"
            @cancel="closeMerge"
        />
    </div>
</template>

<style scoped>
.concept-matching {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    overflow: hidden;
    font-family: var(--p-lingo-font-family);
}

.concept-matching .access-message {
    margin: 1.5rem;
}

.concept-matching .matches-body {
    display: grid;
    grid-template-columns: 22rem 1fr;
    gap: 1.5rem;
    padding: 1.5rem;
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
}

.concept-matching .matches-body.criteria-hidden {
    grid-template-columns: 1fr;
}

.concept-matching .matches-body .matches-criteria {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.concept-matching .matches-criteria .intro {
    margin: 0;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
}

.concept-matching .matches-body .matches-results {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    min-width: 0;
}

.concept-matching .matches-results .results-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
}

.concept-matching .matches-results .unshown-results {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
}

.concept-matching .matches-results .no-runs {
    margin: 0;
    color: var(--p-text-muted-color);
}

@media (max-width: 64rem) {
    .concept-matching .matches-body {
        grid-template-columns: 1fr;
    }
}
</style>
