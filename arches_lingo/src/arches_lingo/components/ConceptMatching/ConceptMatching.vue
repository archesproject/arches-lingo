<script setup lang="ts">
import { computed, ref, watch } from "vue";

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
import type { MatchReviewViewChange } from "@/arches_lingo/components/ConceptMatching/composables/useMatchReviewRoute.ts";

const { $gettext } = useGettext();
const conceptStore = useConceptStore();
const { user, isEditor } = storeToRefs(useUserStore());
const { reportError } = useErrorToast();

const {
    activeRunId,
    candidateStatus,
    pageNumber,
    conceptIdToSearchFrom,
    showView,
} = useMatchReviewRoute(onViewChanged);

const {
    candidates,
    totalResults,
    isLoadingCandidates,
    loadError,
    hasUnshownResults,
    selectedIds,
    loadCandidates,
    changeSelection,
    selectAllOnPage,
    clearSelection,
} = useCandidatePage({
    activeRunId,
    candidateStatus,
    pageNumber,
    onPastLastPage: (lastPageNumber) =>
        showView({ pageNumber: lastPageNumber }, { replace: true }),
});

const {
    runs,
    activeRun,
    activeRunIsUnfinished,
    isCreatingRun,
    loadRuns,
    newestRunId,
    createRun,
} = useConceptMatchRuns({
    activeRunId,
    onRunProgress: () => loadCandidates({ quiet: true }),
    onRunFinished,
});

const showCriteria = ref(true);
const mergingCandidate = ref<ConceptMatchCandidate | null>(null);

let hasInitialized = false;

const selectedCandidateIds = computed(() => Array.from(selectedIds.value));

const dismissedCount = computed(
    () => activeRun.value?.counts_by_status[CANDIDATE_STATUS_DISMISSED] ?? 0,
);

const showNoRunsPrompt = computed(() => !activeRun.value && !runs.value.length);

// The user arrives asynchronously, and every request would be refused for a
// non-editor, so nothing is fetched until they are known to be one.
watch(
    isEditor,
    function (userIsEditor) {
        if (userIsEditor && !hasInitialized) {
            hasInitialized = true;
            initialize();
        }
    },
    { immediate: true },
);

async function initialize(): Promise<void> {
    try {
        await conceptStore.initialize();
    } catch (error) {
        reportError(error, $gettext("Could not load schemes."));
    }

    // Arriving from a concept's own page searches for that concept's matches
    // straight away, replacing the history entry so a reload never repeats it.
    const conceptId = conceptIdToSearchFrom();
    if (conceptId) {
        await startRun({ source_concept_ids: [conceptId] }, { replace: true });
        return;
    }

    await loadRuns();
    if (!(await showNewestRunIfNoneChosen())) {
        await loadCandidates();
    }
}

async function onViewChanged({
    runChanged,
    statusChanged,
}: MatchReviewViewChange): Promise<void> {
    // A page change keeps the selection, so pairs can be gathered across pages.
    if (runChanged || statusChanged) {
        clearSelection();
    }
    if (await showNewestRunIfNoneChosen()) return;
    await loadCandidates();
}

function onRunFinished(): void {
    if (selectedIds.value.size) {
        hasUnshownResults.value = true;
        return;
    }
    loadCandidates();
}

// Replaces rather than pushes: being shown the latest run is part of arriving,
// so going back leaves the page rather than undoing a choice nobody made.
async function showNewestRunIfNoneChosen(): Promise<boolean> {
    const runId = newestRunId();
    if (activeRunId.value !== null || runId === null) {
        return false;
    }
    await showView({ runId, pageNumber: 1 }, { replace: true });
    return true;
}

async function startRun(
    request: ConceptMatchRunRequest,
    { replace = false }: { replace?: boolean } = {},
): Promise<void> {
    const run = await createRun(request);
    if (run) {
        await showView(
            { runId: run.id, pageNumber: 1, status: CANDIDATE_STATUS_PENDING },
            { replace },
        );
    }
}

function onRunRequested(request: ConceptMatchRunRequest): void {
    startRun(request);
}

function onRunSelected({ runId }: { runId: number | null }): void {
    showView({ runId, pageNumber: 1 });
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
        },
        { replace: true },
    );
}

function onMergeRequested({ candidateId }: { candidateId: number }): void {
    mergingCandidate.value =
        candidates.value.find((candidate) => candidate.id === candidateId) ??
        null;
}

// The server settles the pair, so the queue is reloaded rather than patched.
async function onMergeCompleted(): Promise<void> {
    if (mergingCandidate.value) {
        changeSelection({
            candidateId: mergingCandidate.value.id,
            isSelected: false,
        });
    }
    closeMerge();
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
            {{
                $gettext(
                    "Finding matching concepts is available to Lingo editors.",
                )
            }}
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
                        :pending-count="activeRun.pending_count"
                        :dismissed-count="dismissedCount"
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
                    {{ loadError }}
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
                    @selection-changed="changeSelection"
                    @select-all-on-page="selectAllOnPage($event.isSelected)"
                    @page-changed="onPageChanged"
                    @status-changed="onStatusChanged"
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

/* Collapsed, the results take the whole width rather than leaving a gap where
   the criteria were. */
.concept-matching .matches-body.criteria-hidden {
    grid-template-columns: 1fr;
}

.matches-body .matches-criteria {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.matches-criteria .intro {
    margin: 0;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
}

.matches-body .matches-results {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    min-width: 0;
}

.matches-results .results-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
}

.matches-results .unshown-results {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
}

.matches-results .no-runs {
    margin: 0;
    color: var(--p-text-muted-color);
}

@media (max-width: 64rem) {
    .concept-matching .matches-body {
        grid-template-columns: 1fr;
    }
}
</style>
