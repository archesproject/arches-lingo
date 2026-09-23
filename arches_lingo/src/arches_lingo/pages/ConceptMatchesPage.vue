<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import { useGettext } from "vue3-gettext";
import { useRoute, useRouter } from "vue-router";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";
import Message from "primevue/message";
import Select from "primevue/select";

import ConceptMergeDialog from "@/arches_lingo/components/concept/ConceptMerge/ConceptMergeDialog.vue";
import MatchCandidateList from "@/arches_lingo/components/concept-matching/components/MatchCandidateList.vue";
import MatchRunForm from "@/arches_lingo/components/concept-matching/components/MatchRunForm.vue";
import MatchRunProgress from "@/arches_lingo/components/concept-matching/components/MatchRunProgress.vue";
import MatchRunSummary from "@/arches_lingo/components/concept-matching/components/MatchRunSummary.vue";
import MergeDirectionDialog from "@/arches_lingo/components/concept-matching/components/MergeDirectionDialog.vue";

import {
    createConceptMatchRun,
    deleteConceptMatchRun,
    dismissAllConceptMatchCandidates,
    fetchConceptMatchCandidates,
    fetchConceptMatchRuns,
    fetchLingoResource,
    linkConceptMatchCandidates,
    updateConceptMatchCandidates,
} from "@/arches_lingo/api.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";
import {
    CANDIDATES_PER_PAGE,
    CANDIDATE_STATUS_DISMISSED,
    CANDIDATE_STATUS_PENDING,
    RUN_POLL_INTERVAL_MS,
    RUN_STATUS_FAILED,
} from "@/arches_lingo/components/concept-matching/constants.ts";
import {
    buildPreselectedConcept,
    candidateStatusFromRoute,
    describeSkippedReasons,
    isRunUnfinished,
    resolveMergeSides,
} from "@/arches_lingo/components/concept-matching/utils.ts";
import {
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    ERROR,
    SECONDARY,
    SUCCESS,
    WARN,
} from "@/arches_lingo/constants.ts";

import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { storeToRefs } from "pinia";

import type {
    ConceptMatchCandidate,
    ConceptMatchRun,
    ConceptMatchRunRequest,
    MatchedConceptSummary,
    ResourceInstanceResult,
} from "@/arches_lingo/types.ts";

const CONCEPT_GRAPH_SLUG = "concept";

const { $gettext } = useGettext();
const toast = useToast();
const confirm = useConfirm();
const route = useRoute();
const router = useRouter();
const conceptStore = useConceptStore();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

// What the reviewer is looking at -- which run, which page of it, and whether
// they are reading the queue or what they dismissed -- is held in the address
// rather than only in the component, so that going back returns to the queue
// they were reading rather than to the start of it, and a queue can be sent to
// someone else.
function runIdInRoute(): number | null {
    const raw = Array.isArray(route.params.runId)
        ? route.params.runId[0]
        : route.params.runId;
    const runId = Number(raw);
    return raw && Number.isInteger(runId) && runId > 0 ? runId : null;
}

function pageNumberInRoute(): number {
    const pageNumber = Number(route.query.page);
    return Number.isInteger(pageNumber) && pageNumber > 0 ? pageNumber : 1;
}

function statusInRoute(): string {
    return candidateStatusFromRoute(route.query.status);
}

const runs = ref<ConceptMatchRun[]>([]);
const activeRunId = ref<number | null>(runIdInRoute());
const isRunning = ref(false);

const candidates = ref<ConceptMatchCandidate[]>([]);
const selectedIds = ref<Set<number>>(new Set());
const candidateStatus = ref(statusInRoute());
const firstResultIndex = ref((pageNumberInRoute() - 1) * CANDIDATES_PER_PAGE);
const totalResults = ref(0);
const isLoadingCandidates = ref(false);
const isLinking = ref(false);
const isDismissingAll = ref(false);
const isDeletingRun = ref(false);
const showCriteria = ref(true);

const mergingCandidate = ref<ConceptMatchCandidate | null>(null);
const mergeSurvivor = ref<ResourceInstanceResult | null>(null);
const mergeAbsorbedId = ref<string | null>(null);
const isPreparingMerge = ref(false);

let pollTimer: ReturnType<typeof setInterval> | undefined;
let isPollInFlight = false;
const loadError = ref<string | null>(null);

const activeRun = computed(function () {
    return runs.value.find((run) => run.id === activeRunId.value);
});

// Cancelling and deleting are the same action on the same button: a run that is
// still working is stopped and removed, one that has finished is just removed.
const activeRunIsUnfinished = computed(function () {
    return Boolean(activeRun.value && isRunUnfinished(activeRun.value));
});

function reportError(error: unknown, summary: string) {
    toast.add({
        severity: ERROR,
        life: DEFAULT_ERROR_TOAST_LIFE,
        summary,
        detail: error instanceof Error ? error.message : undefined,
    });
}

async function loadRuns() {
    try {
        runs.value = (await fetchConceptMatchRuns()).data;
    } catch (error) {
        reportError(error, $gettext("Could not load previous runs."));
    }
}

/**
 * Show the newest run when the address does not name one.
 *
 * Replaces rather than pushes: landing on the page and being shown the latest
 * run is one step, so going back should leave the page rather than undo a
 * choice the reviewer did not make.
 */
async function showNewestRunIfNoneChosen() {
    if (activeRunId.value !== null || !runs.value.length) {
        return false;
    }
    await router.replace(
        routeForView({ runId: runs.value[0].id, pageNumber: 1 }),
    );
    return true;
}

async function loadCandidates({ quiet = false } = {}) {
    if (activeRunId.value === null) {
        candidates.value = [];
        totalResults.value = 0;
        return;
    }

    // A poll refreshes the list in place. Showing the loading state every two
    // seconds would flicker the pairs the reviewer is trying to read, so only a
    // refresh they asked for announces itself.
    if (!quiet) isLoadingCandidates.value = true;
    loadError.value = null;
    try {
        const page = await fetchConceptMatchCandidates(
            activeRunId.value,
            candidateStatus.value,
            Math.floor(firstResultIndex.value / CANDIDATES_PER_PAGE) + 1,
            CANDIDATES_PER_PAGE,
        );
        candidates.value = page.data;
        totalResults.value = page.total_results;
    } catch (error) {
        loadError.value =
            error instanceof Error ? error.message : String(error);
    } finally {
        if (!quiet) isLoadingCandidates.value = false;
    }
}

// A fuzzy run is handed to a worker and comes back still pending, so the run is
// polled until it settles rather than reporting a count of zero straight away.
function stopPolling() {
    if (pollTimer !== undefined) {
        clearInterval(pollTimer);
        pollTimer = undefined;
    }
}

function pollUntilFinished(runId: number) {
    stopPolling();
    pollTimer = setInterval(async () => {
        // Two requests a tick against a run that may hold tens of thousands of
        // pairs: a tick that is still in flight is skipped rather than queued
        // behind itself.
        if (isPollInFlight) return;
        isPollInFlight = true;
        try {
            // The listing is refreshed on every tick rather than only at the
            // end, so the running count climbs in front of the reviewer instead
            // of sitting at zero until the search finishes.
            runs.value = (await fetchConceptMatchRuns()).data;
            const run = runs.value.find(
                (candidateRun) => candidateRun.id === runId,
            );
            if (!run) {
                // Cancelled, from here or from somewhere else. There is no
                // longer anything to wait for.
                stopPolling();
                isRunning.value = false;
                return;
            }
            if (isRunUnfinished(run)) {
                // Pairs are stored as they are found, so the list is refreshed
                // alongside the count: the reviewer can start reading results
                // while the rest of the search is still running.
                await loadCandidates({ quiet: true });
                return;
            }

            stopPolling();
            isRunning.value = false;
            await loadCandidates();
            reportRunFinished(run);
        } finally {
            isPollInFlight = false;
        }
    }, RUN_POLL_INTERVAL_MS);
}

function reportRunFinished(run: ConceptMatchRun) {
    if (run.status === RUN_STATUS_FAILED) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Match detection failed"),
            detail: run.error_message || undefined,
        });
        return;
    }
    toast.add({
        severity: SUCCESS,
        life: DEFAULT_TOAST_LIFE,
        summary: $gettext("Found %{count} candidate pair(s)", {
            count: String(run.candidate_count),
        }),
    });
}

async function onRun(request: ConceptMatchRunRequest) {
    isRunning.value = true;
    try {
        const run = await createConceptMatchRun(request);
        await loadRuns();
        await router.push(
            routeForView({
                runId: run.id,
                pageNumber: 1,
                status: CANDIDATE_STATUS_PENDING,
            }),
        );

        if (isRunUnfinished(run)) {
            pollUntilFinished(run.id);
            return;
        }
        reportRunFinished(run);
    } catch (error) {
        reportError(error, $gettext("Could not detect matches."));
        isRunning.value = false;
    } finally {
        if (!pollTimer) isRunning.value = false;
    }
}

async function setStatusForSelection(status: string) {
    if (activeRunId.value === null || !selectedIds.value.size) return;

    try {
        const result = await updateConceptMatchCandidates(
            activeRunId.value,
            Array.from(selectedIds.value),
            status,
        );
        toast.add({
            severity: SUCCESS,
            life: DEFAULT_TOAST_LIFE,
            summary:
                status === CANDIDATE_STATUS_DISMISSED
                    ? $gettext("Dismissed %{count} pair(s)", {
                          count: String(result.updated),
                      })
                    : $gettext("Returned %{count} pair(s) to the queue", {
                          count: String(result.updated),
                      }),
        });
        selectedIds.value = new Set();
        await Promise.all([loadRuns(), loadCandidates()]);
    } catch (error) {
        reportError(error, $gettext("Could not update the selected pairs."));
    }
}

function onDismissAllRemaining() {
    const run = activeRun.value;
    if (!run || !run.pending_count) return;

    confirm.require({
        group: "dismiss-all-matches",
        header: $gettext("Dismiss everything left?"),
        message: $gettext(
            "All %{count} pair(s) still awaiting a decision will be dismissed. They stay in the run, and can be restored from the dismissed list.",
            { count: String(run.pending_count) },
        ),
        accept: async () => {
            isDismissingAll.value = true;
            try {
                const result = await dismissAllConceptMatchCandidates(run.id);
                toast.add({
                    severity: SUCCESS,
                    life: DEFAULT_TOAST_LIFE,
                    summary: $gettext("Dismissed %{count} pair(s)", {
                        count: String(result.updated),
                    }),
                });
                selectedIds.value = new Set();
                await Promise.all([loadRuns(), loadCandidates()]);
            } catch (error) {
                reportError(
                    error,
                    $gettext("Could not dismiss the remaining pairs."),
                );
            } finally {
                isDismissingAll.value = false;
            }
        },
    });
}

function onDeleteRun() {
    const run = activeRun.value;
    if (!run) return;
    const isUnfinished = activeRunIsUnfinished.value;

    confirm.require({
        group: "delete-match-run",
        header: isUnfinished
            ? $gettext("Cancel this run?")
            : $gettext("Delete this run?"),
        message: isUnfinished
            ? $gettext(
                  "The search stops, and the run and everything it has found so far are deleted. This cannot be undone.",
              )
            : $gettext(
                  "The run and all %{count} of its pairs are deleted. This cannot be undone.",
                  { count: String(run.candidate_count) },
              ),
        accept: async () => {
            isDeletingRun.value = true;
            try {
                await deleteConceptMatchRun(run.id);
                stopPolling();
                isRunning.value = false;
                selectedIds.value = new Set();
                await loadRuns();
                await router.replace(
                    routeForView({
                        runId: runs.value.length ? runs.value[0].id : null,
                        pageNumber: 1,
                        status: CANDIDATE_STATUS_PENDING,
                    }),
                );
                toast.add({
                    severity: SUCCESS,
                    life: DEFAULT_TOAST_LIFE,
                    summary: isUnfinished
                        ? $gettext("Run cancelled")
                        : $gettext("Run deleted"),
                });
            } catch (error) {
                reportError(
                    error,
                    isUnfinished
                        ? $gettext("Could not cancel the run.")
                        : $gettext("Could not delete the run."),
                );
            } finally {
                isDeletingRun.value = false;
            }
        },
    });
}

// A pair can be skipped for a reason the reviewer can act on, so the reasons
// are named rather than reported as a bare count.
function describeSkipped(skipped: Record<string, number>) {
    return describeSkippedReasons(skipped, {
        missing_uri: $gettext("no URI to point at"),
        not_editable: $gettext("neither concept can be edited"),
        missing_concept: $gettext("concept no longer exists"),
    });
}

async function onLinkSelection() {
    if (activeRunId.value === null || !selectedIds.value.size) return;

    isLinking.value = true;
    try {
        const result = await linkConceptMatchCandidates(
            activeRunId.value,
            Array.from(selectedIds.value),
        );

        const detail = [];
        if (result.linked_one_way) {
            detail.push(
                $gettext(
                    "%{count} recorded on one side only, because the other concept cannot be edited.",
                    { count: String(result.linked_one_way) },
                ),
            );
        }
        if (Object.keys(result.skipped).length) {
            detail.push(
                $gettext("Skipped: %{reasons}.", {
                    reasons: describeSkipped(result.skipped),
                }),
            );
        }

        toast.add({
            severity: result.linked ? SUCCESS : WARN,
            life: DEFAULT_TOAST_LIFE,
            summary: $gettext("Linked %{count} pair(s)", {
                count: String(result.linked),
            }),
            detail: detail.join(" ") || undefined,
        });

        selectedIds.value = new Set();
        await Promise.all([loadRuns(), loadCandidates()]);
    } catch (error) {
        reportError(error, $gettext("Could not link the selected pairs."));
    } finally {
        isLinking.value = false;
    }
}

// Which side of the pair is which, once the reviewer has chosen a survivor.
const mergeSides = computed(function () {
    if (!mergingCandidate.value || !mergeAbsorbedId.value) return null;
    return resolveMergeSides(mergingCandidate.value, mergeAbsorbedId.value);
});

// The merge dialog takes the absorbed concept in the shape its picker emits.
// Only the id and labels are read from it: the id to fetch the resource, the
// labels to name it.
const preselectedAbsorbedConcept = computed(function () {
    return mergeSides.value
        ? buildPreselectedConcept(mergeSides.value.absorbed)
        : undefined;
});

function nameOf(concept: MatchedConceptSummary) {
    return getItemLabel(
        concept,
        selectedLanguage.value.code,
        systemLanguage.value.code,
    ).value;
}

function onMergeRequested(candidateId: number) {
    mergingCandidate.value =
        candidates.value.find((candidate) => candidate.id === candidateId) ??
        null;
}

// The pair is symmetric, so the reviewer says which concept survives; only then
// is the surviving concept fetched in the shape the merge dialog expects.
async function onDirectionChosen(survivorId: string, absorbedId: string) {
    const candidate = mergingCandidate.value;
    if (!candidate) return;

    isPreparingMerge.value = true;
    try {
        mergeSurvivor.value = await fetchLingoResource(
            CONCEPT_GRAPH_SLUG,
            survivorId,
        );
        mergeAbsorbedId.value = absorbedId;
    } catch (error) {
        reportError(error, $gettext("Could not open the merge."));
        mergingCandidate.value = null;
    } finally {
        isPreparingMerge.value = false;
    }
}

function closeMerge() {
    mergingCandidate.value = null;
    mergeSurvivor.value = null;
    mergeAbsorbedId.value = null;
}

async function onMergeCompleted() {
    closeMerge();
    toast.add({
        severity: SUCCESS,
        life: DEFAULT_TOAST_LIFE,
        summary: $gettext("Concepts merged"),
    });
    // The server settles the pair, so the queue is reloaded rather than patched.
    await Promise.all([loadRuns(), loadCandidates()]);
}

function onSelectionChange(candidateId: number, isSelected: boolean) {
    const updated = new Set(selectedIds.value);
    if (isSelected) {
        updated.add(candidateId);
    } else {
        updated.delete(candidateId);
    }
    selectedIds.value = updated;
}

function onSelectAllOnPage(isSelected: boolean) {
    const updated = new Set(selectedIds.value);
    for (const candidate of candidates.value) {
        if (isSelected) {
            updated.add(candidate.id);
        } else {
            updated.delete(candidate.id);
        }
    }
    selectedIds.value = updated;
}

/**
 * Where to send the browser for a given view of the queue.
 *
 * Only what differs from the default is written down, so the ordinary case --
 * the first page of a run's outstanding pairs -- stays a plain, sendable link.
 */
function routeForView({
    runId = activeRunId.value,
    pageNumber = Math.floor(firstResultIndex.value / CANDIDATES_PER_PAGE) + 1,
    status = candidateStatus.value,
}: {
    runId?: number | null;
    pageNumber?: number;
    status?: string;
} = {}) {
    const query: Record<string, string> = {};
    if (pageNumber > 1) {
        query.page = String(pageNumber);
    }
    if (status !== CANDIDATE_STATUS_PENDING) {
        query.status = status;
    }
    return {
        name: routeNames.conceptMatches,
        params: runId === null ? {} : { runId: String(runId) },
        query,
    };
}

function onRunSelected(runId: number | null) {
    router.push(
        routeForView({ runId, pageNumber: 1, status: candidateStatus.value }),
    );
}

function onPageChange(newFirstResultIndex: number) {
    router.push(
        routeForView({
            pageNumber:
                Math.floor(newFirstResultIndex / CANDIDATES_PER_PAGE) + 1,
        }),
    );
}

function onStatusChange(newStatus: string) {
    router.push(routeForView({ pageNumber: 1, status: newStatus }));
}

// The address is the single source of truth for which queue is shown, so this
// is the only place the view is loaded: a click and a press of the back button
// arrive here by the same path.
watch(
    () => [route.params.runId, route.query.page, route.query.status],
    function () {
        const runIdChanged = activeRunId.value !== runIdInRoute();
        const statusChanged = candidateStatus.value !== statusInRoute();

        activeRunId.value = runIdInRoute();
        candidateStatus.value = statusInRoute();
        firstResultIndex.value =
            (pageNumberInRoute() - 1) * CANDIDATES_PER_PAGE;

        // A run or status change starts the review over; a page change keeps
        // the selection, so a reviewer can gather pairs across pages.
        if (runIdChanged || statusChanged) {
            selectedIds.value = new Set();
        }
        loadCandidates();
    },
);

onBeforeUnmount(stopPolling);

onMounted(async () => {
    try {
        await conceptStore.initialize();
    } catch (error) {
        reportError(error, $gettext("Could not load schemes."));
    }

    // Arriving from a concept's own page: look for that concept's matches
    // straight away rather than making the reviewer re-enter what they just
    // came from. A run this narrow takes well under a second.
    const conceptId = route.query.concept;
    if (typeof conceptId === "string" && conceptId) {
        await onRun({ source_concept_ids: [conceptId] });
        return;
    }

    await loadRuns();
    // The address may already name a run -- a link, or a reload. Only fall back
    // to the newest when it does not.
    if (!(await showNewestRunIfNoneChosen())) {
        await loadCandidates();
    }

    // Coming back to a search that is still going: resume watching it rather
    // than showing a stale, empty queue.
    if (activeRun.value && isRunUnfinished(activeRun.value)) {
        isRunning.value = true;
        pollUntilFinished(activeRun.value.id);
    }
});
</script>

<template>
    <div class="matches-page">
        <div class="matches-header">
            <h2 class="matches-header-title">
                <i
                    class="pi pi-clone"
                    aria-hidden="true"
                />
                {{ $gettext("Find Matching Concepts") }}
            </h2>
            <Button
                :label="
                    showCriteria
                        ? $gettext('Hide Search Options')
                        : $gettext('Show Search Options')
                "
                :icon="
                    showCriteria ? 'pi pi-angle-double-left' : 'pi pi-sliders-h'
                "
                :class="'side-panel-toggle'"
                size="small"
                @click="showCriteria = !showCriteria"
            />
        </div>

        <div
            class="matches-body"
            :class="{ 'criteria-hidden': !showCriteria }"
        >
            <div
                v-show="showCriteria"
                class="matches-criteria"
            >
                <p class="matches-intro">
                    {{
                        $gettext(
                            "Look for concepts that probably mean the same thing, then dismiss the ones that do not.",
                        )
                    }}
                </p>

                <MatchRunForm
                    :schemes="conceptStore.schemes"
                    :is-running="isRunning"
                    @run="onRun"
                />
            </div>

            <div class="matches-results">
                <div class="matches-results-header">
                    <Select
                        :model-value="activeRunId"
                        :options="runs"
                        option-value="id"
                        :placeholder="$gettext('No runs yet')"
                        :disabled="!runs.length"
                        class="run-select"
                        @update:model-value="onRunSelected"
                    >
                        <template #value="{ value }">
                            <span v-if="activeRun">
                                <span
                                    v-if="activeRun.name"
                                    class="run-option-name"
                                    >{{ activeRun.name }} — </span
                                >{{
                                    $gettext(
                                        "%{pending} of %{total} left to review",
                                        {
                                            pending: String(
                                                activeRun.pending_count,
                                            ),
                                            total: String(
                                                activeRun.candidate_count,
                                            ),
                                        },
                                    )
                                }}
                            </span>
                            <span v-else>{{ value }}</span>
                        </template>
                        <template #option="{ option }">
                            <span
                                v-if="option.name"
                                class="run-option-name"
                                >{{ option.name }} — </span
                            >{{
                                $gettext("%{count} pairs", {
                                    count: String(option.candidate_count),
                                })
                            }}
                            — {{ new Date(option.created).toLocaleString() }}
                        </template>
                    </Select>

                    <div class="matches-actions">
                        <Button
                            v-if="candidateStatus === CANDIDATE_STATUS_PENDING"
                            icon="pi pi-link"
                            :label="
                                $gettext('Link %{count}', {
                                    count: String(selectedIds.size),
                                })
                            "
                            :disabled="!selectedIds.size || isLinking"
                            :loading="isLinking"
                            class="action-button"
                            @click="onLinkSelection"
                        />
                        <Button
                            v-if="candidateStatus === CANDIDATE_STATUS_PENDING"
                            icon="pi pi-times"
                            :label="
                                $gettext('Dismiss %{count}', {
                                    count: String(selectedIds.size),
                                })
                            "
                            :severity="SECONDARY"
                            :outlined="true"
                            :disabled="!selectedIds.size"
                            class="action-button"
                            @click="
                                setStatusForSelection(
                                    CANDIDATE_STATUS_DISMISSED,
                                )
                            "
                        />
                        <Button
                            v-else-if="
                                candidateStatus === CANDIDATE_STATUS_DISMISSED
                            "
                            icon="pi pi-undo"
                            :label="
                                $gettext('Restore %{count}', {
                                    count: String(selectedIds.size),
                                })
                            "
                            :severity="SECONDARY"
                            :outlined="true"
                            :disabled="!selectedIds.size"
                            class="action-button"
                            @click="
                                setStatusForSelection(CANDIDATE_STATUS_PENDING)
                            "
                        />
                        <Button
                            v-if="
                                candidateStatus === CANDIDATE_STATUS_PENDING &&
                                activeRun &&
                                activeRun.pending_count > 0
                            "
                            icon="pi pi-times-circle"
                            :label="
                                $gettext('Dismiss all %{count}', {
                                    count: String(activeRun!.pending_count),
                                })
                            "
                            :severity="SECONDARY"
                            :outlined="true"
                            :disabled="isDismissingAll"
                            :loading="isDismissingAll"
                            class="action-button"
                            @click="onDismissAllRemaining"
                        />
                        <Button
                            v-if="activeRun"
                            :icon="
                                activeRunIsUnfinished
                                    ? 'pi pi-ban'
                                    : 'pi pi-trash'
                            "
                            :label="
                                activeRunIsUnfinished
                                    ? $gettext('Cancel run')
                                    : $gettext('Delete run')
                            "
                            :severity="DANGER"
                            :outlined="true"
                            :disabled="isDeletingRun"
                            :loading="isDeletingRun"
                            class="action-button"
                            @click="onDeleteRun"
                        />
                    </div>
                </div>

                <MatchRunSummary
                    v-if="activeRun"
                    :run="activeRun"
                    :schemes="conceptStore.schemes"
                />

                <MatchRunProgress
                    v-if="activeRun && isRunUnfinished(activeRun)"
                    :run="activeRun"
                />

                <Message
                    v-if="loadError"
                    :severity="ERROR"
                    :closable="false"
                >
                    {{ loadError }}
                </Message>

                <MatchCandidateList
                    :candidates="candidates"
                    :selected-ids="selectedIds"
                    :is-loading="isLoadingCandidates"
                    :total-results="totalResults"
                    :items-per-page="CANDIDATES_PER_PAGE"
                    :first-result-index="firstResultIndex"
                    :status="candidateStatus"
                    :counts-by-status="activeRun?.counts_by_status"
                    @update:selected="onSelectionChange"
                    @select-all-on-page="onSelectAllOnPage"
                    @page="onPageChange"
                    @set-status="onStatusChange"
                    @merge="onMergeRequested"
                />
            </div>
        </div>

        <ConfirmDialog group="dismiss-all-matches" />
        <ConfirmDialog group="delete-match-run" />

        <MergeDirectionDialog
            v-if="mergingCandidate && !mergeSurvivor"
            :concept-a="mergingCandidate.concept_a"
            :concept-b="mergingCandidate.concept_b"
            :name-of="nameOf"
            :is-loading="isPreparingMerge"
            @confirm="onDirectionChosen"
            @cancel="closeMerge"
        />

        <ConceptMergeDialog
            v-if="mergeSurvivor && mergeAbsorbedId && mergingCandidate"
            :survivor-concept="mergeSurvivor"
            :survivor-label="
                mergeSides ? nameOf(mergeSides.survivor) : undefined
            "
            :scheme-id="mergeSides?.survivor.scheme_id ?? ''"
            :graph-slug="CONCEPT_GRAPH_SLUG"
            :preselected-concept="preselectedAbsorbedConcept"
            @merged="onMergeCompleted"
            @cancel="closeMerge"
        />
    </div>
</template>

<style scoped>
.matches-page {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    overflow: hidden;
    font-family: var(--p-lingo-font-family);
}

.matches-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    row-gap: 0.5rem;
    min-height: 3rem;
    padding: 0.375rem 1rem;
    background: var(--p-header-toolbar-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    flex-shrink: 0;
    box-sizing: border-box;
}

.matches-header-title {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    margin: 0;
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-text-color);
}

.matches-header-title .pi {
    font-size: var(--p-lingo-font-size-medium);
}

.side-panel-toggle {
    font-size: var(--p-lingo-font-size-small) !important;
    font-weight: var(--p-lingo-font-weight-normal) !important;
    border-radius: 0.125rem !important;
    background: var(--p-header-button-background) !important;
    color: var(--p-header-button-color) !important;
    border-color: var(--p-header-button-border) !important;
    border-style: solid !important;
    border-width: 0.0625rem !important;
}

.side-panel-toggle:hover {
    background: var(--p-highlight-background) !important;
}

.matches-body {
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
.matches-body.criteria-hidden {
    grid-template-columns: 1fr;
}

.matches-criteria {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.matches-intro {
    margin: 0;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
}

.matches-results {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    min-width: 0;
}

.run-option-name {
    font-weight: var(--p-lingo-font-weight-bold);
}

.matches-results-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
}

.matches-actions {
    display: flex;
    gap: 0.5rem;
}

.action-button,
.run-select {
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
}

@media (max-width: 64rem) {
    .matches-page {
        grid-template-columns: 1fr;
    }
}
</style>
