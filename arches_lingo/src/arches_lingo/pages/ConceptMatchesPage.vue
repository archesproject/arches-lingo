<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { storeToRefs } from "pinia";
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

import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import {
    createConceptMatchRun,
    deleteConceptMatchRun,
    fetchConceptMatchCandidates,
    fetchConceptMatchRun,
    fetchConceptMatchRuns,
    fetchLingoResource,
    linkConceptMatchCandidates,
    updateAllConceptMatchCandidates,
    updateConceptMatchCandidates,
} from "@/arches_lingo/api.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";
import {
    CANDIDATES_PER_PAGE,
    CANDIDATE_STATUS_DISMISSED,
    CANDIDATE_STATUS_PENDING,
    RUN_POLL_FAILURE_LIMIT,
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
    INFO,
    SECONDARY,
    SUCCESS,
    WARN,
} from "@/arches_lingo/constants.ts";

import type {
    ConceptMatchCandidate,
    ConceptMatchRun,
    ConceptMatchRunRequest,
    ConceptMatchStatusChange,
    MatchedConceptSummary,
    ResourceInstanceResult,
} from "@/arches_lingo/types.ts";

const CONCEPT_GRAPH_SLUG = "concept";

const { $gettext, $ngettext } = useGettext();
const toast = useToast();
const confirm = useConfirm();
const route = useRoute();
const router = useRouter();
const conceptStore = useConceptStore();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());
const { user, isEditor } = storeToRefs(useUserStore());

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
const isCreatingRun = ref(false);

const candidates = ref<ConceptMatchCandidate[]>([]);
const selectedIds = ref<Set<number>>(new Set());
const candidateStatus = ref(statusInRoute());
const firstResultIndex = ref((pageNumberInRoute() - 1) * CANDIDATES_PER_PAGE);
const totalResults = ref(0);
const isLoadingCandidates = ref(false);
const isLinking = ref(false);
const isUpdatingSelection = ref(false);
const isChangingAll = ref(false);
const isDeletingRun = ref(false);
// While pairs are selected, a refresh would move rows under the reviewer; new
// results wait until they ask for them.
const hasUnshownResults = ref(false);
const showCriteria = ref(true);

const mergingCandidate = ref<ConceptMatchCandidate | null>(null);
const mergeSurvivor = ref<ResourceInstanceResult | null>(null);
const mergeAbsorbedId = ref<string | null>(null);
const isPreparingMerge = ref(false);

let pollTimer: ReturnType<typeof setInterval> | undefined;
let isPollInFlight = false;
let consecutivePollFailures = 0;
// Only the newest response for each is shown, whatever order they arrive in.
let latestRunsRequest = 0;
let latestCandidatesRequest = 0;
let loadingCandidatesRequest = 0;
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
    const requestNumber = ++latestRunsRequest;
    try {
        const listedRuns = (await fetchConceptMatchRuns()).data;
        if (requestNumber === latestRunsRequest) {
            runs.value = listedRuns;
        }
    } catch (error) {
        reportError(error, $gettext("Could not load previous runs."));
    }
}

// Every editor sees every run, so the default is the viewer's own newest.
function newestRunId() {
    const newestOwnRun = runs.value.find((run) => run.started_by_viewer);
    return (newestOwnRun ?? runs.value[0])?.id ?? null;
}

/**
 * Show the newest run when the address does not name one.
 *
 * Replaces rather than pushes: landing on the page and being shown the latest
 * run is one step, so going back should leave the page rather than undo a
 * choice the reviewer did not make.
 */
async function showNewestRunIfNoneChosen() {
    const runId = newestRunId();
    if (activeRunId.value !== null || runId === null) {
        return false;
    }
    await router.replace(routeForView({ runId, pageNumber: 1 }));
    return true;
}

async function loadCandidates({ quiet = false } = {}) {
    if (activeRunId.value === null) {
        candidates.value = [];
        totalResults.value = 0;
        return;
    }

    if (quiet && selectedIds.value.size) {
        hasUnshownResults.value = true;
        return;
    }

    const requestNumber = ++latestCandidatesRequest;
    // A poll refreshes the list in place. Showing the loading state every two
    // seconds would flicker the pairs the reviewer is trying to read, so only a
    // refresh they asked for announces itself.
    if (!quiet) {
        isLoadingCandidates.value = true;
        loadingCandidatesRequest = requestNumber;
        hasUnshownResults.value = false;
    }
    loadError.value = null;
    const pageNumber =
        Math.floor(firstResultIndex.value / CANDIDATES_PER_PAGE) + 1;
    try {
        const page = await fetchConceptMatchCandidates(
            activeRunId.value,
            candidateStatus.value,
            pageNumber,
            CANDIDATES_PER_PAGE,
        );
        if (requestNumber !== latestCandidatesRequest) return;
        // Deciding the last pairs on the last page, or a stale link, leaves the
        // address past the end of the queue.
        const lastPageNumber = Math.max(
            1,
            Math.ceil(page.total_results / CANDIDATES_PER_PAGE),
        );
        if (!page.data.length && pageNumber > lastPageNumber) {
            await router.replace(routeForView({ pageNumber: lastPageNumber }));
            return;
        }
        candidates.value = page.data;
        totalResults.value = page.total_results;
    } catch (error) {
        if (requestNumber === latestCandidatesRequest) {
            loadError.value =
                error instanceof Error ? error.message : String(error);
        }
    } finally {
        if (loadingCandidatesRequest === requestNumber) {
            isLoadingCandidates.value = false;
        }
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
    consecutivePollFailures = 0;
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
            const run = await fetchConceptMatchRun(runId);
            consecutivePollFailures = 0;
            if (runId !== activeRunId.value) return;
            if (!run) {
                // Cancelled, from here or from somewhere else. There is no
                // longer anything to wait for.
                stopPolling();
                await loadRuns();
                return;
            }
            runs.value = runs.value.map((listedRun) =>
                listedRun.id === runId ? run : listedRun,
            );
            if (isRunUnfinished(run)) {
                // Pairs are stored as they are found, so the list is refreshed
                // alongside the count: the reviewer can start reading results
                // while the rest of the search is still running.
                await loadCandidates({ quiet: true });
                return;
            }

            stopPolling();
            if (selectedIds.value.size) {
                hasUnshownResults.value = true;
            } else {
                await loadCandidates();
            }
            reportRunFinished(run);
        } catch (error) {
            consecutivePollFailures += 1;
            if (consecutivePollFailures >= RUN_POLL_FAILURE_LIMIT) {
                stopPolling();
                reportError(
                    error,
                    $gettext(
                        "Lost touch with the running search. Reload the page to check on it.",
                    ),
                );
            }
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
        summary: $ngettext(
            "Found %{count} candidate pair",
            "Found %{count} candidate pairs",
            run.candidate_count,
            { count: String(run.candidate_count) },
        ),
    });
}

async function onRun(
    request: ConceptMatchRunRequest,
    { replaceRoute = false } = {},
) {
    isCreatingRun.value = true;
    try {
        const run = await createConceptMatchRun(request);
        await loadRuns();
        const runView = routeForView({
            runId: run.id,
            pageNumber: 1,
            status: CANDIDATE_STATUS_PENDING,
        });
        await (replaceRoute ? router.replace(runView) : router.push(runView));

        if (!isRunUnfinished(run)) {
            reportRunFinished(run);
        }
    } catch (error) {
        reportError(error, $gettext("Could not detect matches."));
    } finally {
        isCreatingRun.value = false;
    }
}

// A pair can be skipped for a reason the reviewer can act on, so the reasons
// are named rather than reported as a bare count.
function describeSkipped(skipped: Record<string, number>) {
    const reasonLabels: Record<string, string> = {
        missing_uri: $gettext("no URI to point at"),
        not_editable: $gettext("neither concept can be edited"),
        missing_concept: $gettext("concept no longer exists"),
        already_decided: $gettext("already dismissed, linked or merged"),
    };
    return describeSkippedReasons(
        skipped,
        (reason, count) =>
            $gettext("%{count} (%{reason})", {
                count: String(count),
                reason: reasonLabels[reason] ?? reason,
            }),
        selectedLanguage.value.code,
    );
}

function describeSkippedDetail(skipped: Record<string, number>) {
    if (!Object.keys(skipped).length) return undefined;
    return $gettext("Skipped: %{reasons}.", {
        reasons: describeSkipped(skipped),
    });
}

function reportStatusChange(result: ConceptMatchStatusChange) {
    toast.add({
        severity: result.updated ? SUCCESS : WARN,
        life: DEFAULT_TOAST_LIFE,
        summary:
            result.status === CANDIDATE_STATUS_DISMISSED
                ? $ngettext(
                      "Dismissed %{count} pair",
                      "Dismissed %{count} pairs",
                      result.updated,
                      { count: String(result.updated) },
                  )
                : $ngettext(
                      "Returned %{count} pair to the queue",
                      "Returned %{count} pairs to the queue",
                      result.updated,
                      { count: String(result.updated) },
                  ),
        detail: describeSkippedDetail(result.skipped),
    });
}

async function setStatusForSelection(status: string) {
    if (activeRunId.value === null || !selectedIds.value.size) return;

    isUpdatingSelection.value = true;
    try {
        reportStatusChange(
            await updateConceptMatchCandidates(
                activeRunId.value,
                Array.from(selectedIds.value),
                status,
            ),
        );
        selectedIds.value = new Set();
        await Promise.all([loadRuns(), loadCandidates()]);
    } catch (error) {
        reportError(error, $gettext("Could not update the selected pairs."));
    } finally {
        isUpdatingSelection.value = false;
    }
}

function confirmStatusChangeForAll(status: string) {
    const run = activeRun.value;
    if (!run) return;
    const isDismissing = status === CANDIDATE_STATUS_DISMISSED;
    const affectedCount = isDismissing
        ? run.pending_count
        : run.counts_by_status[CANDIDATE_STATUS_DISMISSED] ?? 0;
    if (!affectedCount) return;

    confirm.require({
        group: "change-all-matches",
        header: isDismissing
            ? $gettext("Dismiss everything left?")
            : $gettext("Restore everything dismissed?"),
        message: isDismissing
            ? $ngettext(
                  "The %{count} pair still awaiting a decision will be dismissed. It stays in the run, and can be restored from the dismissed list.",
                  "All %{count} pairs still awaiting a decision will be dismissed. They stay in the run, and can be restored from the dismissed list.",
                  affectedCount,
                  { count: String(affectedCount) },
              )
            : $ngettext(
                  "The %{count} dismissed pair will be returned to the queue, unless it has been linked or merged since.",
                  "All %{count} dismissed pairs will be returned to the queue, except any linked or merged since.",
                  affectedCount,
                  { count: String(affectedCount) },
              ),
        accept: async () => {
            isChangingAll.value = true;
            try {
                reportStatusChange(
                    await updateAllConceptMatchCandidates(run.id, status),
                );
                selectedIds.value = new Set();
                await Promise.all([loadRuns(), loadCandidates()]);
            } catch (error) {
                reportError(
                    error,
                    isDismissing
                        ? $gettext("Could not dismiss the remaining pairs.")
                        : $gettext("Could not restore the dismissed pairs."),
                );
            } finally {
                isChangingAll.value = false;
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
            : $ngettext(
                  "The run and its %{count} pair are deleted. This cannot be undone.",
                  "The run and all %{count} of its pairs are deleted. This cannot be undone.",
                  run.candidate_count,
                  { count: String(run.candidate_count) },
              ),
        accept: async () => {
            isDeletingRun.value = true;
            try {
                await deleteConceptMatchRun(run.id);
                selectedIds.value = new Set();
                await loadRuns();
                await router.replace(
                    routeForView({
                        runId: newestRunId(),
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

async function onLinkSelection() {
    if (activeRunId.value === null || !selectedIds.value.size) return;

    isLinking.value = true;
    try {
        const result = await linkConceptMatchCandidates(
            activeRunId.value,
            Array.from(selectedIds.value),
        );

        const oneWayDetail = result.linked_one_way
            ? $ngettext(
                  "%{count} recorded on one side only, because the other concept cannot be edited.",
                  "%{count} recorded on one side only, because the other concepts cannot be edited.",
                  result.linked_one_way,
                  { count: String(result.linked_one_way) },
              )
            : undefined;
        const skippedDetail = describeSkippedDetail(result.skipped);

        toast.add({
            severity: result.linked ? SUCCESS : WARN,
            life: DEFAULT_TOAST_LIFE,
            summary: $ngettext(
                "Linked %{count} pair",
                "Linked %{count} pairs",
                result.linked,
                { count: String(result.linked) },
            ),
            detail:
                oneWayDetail && skippedDetail
                    ? $gettext("%{oneWay} %{skipped}", {
                          oneWay: oneWayDetail,
                          skipped: skippedDetail,
                      })
                    : oneWayDetail ?? skippedDetail,
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
    const mergedCandidateId = mergingCandidate.value?.id;
    closeMerge();
    if (mergedCandidateId !== undefined) {
        const updated = new Set(selectedIds.value);
        updated.delete(mergedCandidateId);
        selectedIds.value = updated;
    }
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

function describeRunOption(run: ConceptMatchRun) {
    const details = {
        name: run.name,
        count: String(run.candidate_count),
        started: new Date(run.created).toLocaleString(
            selectedLanguage.value.code,
        ),
        creator: run.created_by ?? $gettext("Command line"),
    };
    return run.name
        ? $ngettext(
              "%{name} — %{count} pair — %{started} — %{creator}",
              "%{name} — %{count} pairs — %{started} — %{creator}",
              run.candidate_count,
              details,
          )
        : $ngettext(
              "%{count} pair — %{started} — %{creator}",
              "%{count} pairs — %{started} — %{creator}",
              run.candidate_count,
              details,
          );
}

const activeRunDescription = computed(function () {
    const run = activeRun.value;
    if (!run) return "";
    const counts = {
        name: run.name,
        pending: String(run.pending_count),
        total: String(run.candidate_count),
    };
    return run.name
        ? $gettext("%{name} — %{pending} of %{total} left to review", counts)
        : $gettext("%{pending} of %{total} left to review", counts);
});

const dismissedCount = computed(
    () => activeRun.value?.counts_by_status[CANDIDATE_STATUS_DISMISSED] ?? 0,
);

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
    async function () {
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
        if (await showNewestRunIfNoneChosen()) return;
        loadCandidates();
    },
);

// Whichever run is on screen is the one watched, however it got there.
watch(
    () => (activeRunIsUnfinished.value ? activeRunId.value : null),
    function (unfinishedRunId) {
        if (unfinishedRunId === null) {
            stopPolling();
            return;
        }
        pollUntilFinished(unfinishedRunId);
    },
);

onBeforeUnmount(stopPolling);

let hasInitialized = false;

// The user arrives asynchronously; nothing is fetched until they are known to be
// an editor, since every request would otherwise be refused.
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

async function initialize() {
    try {
        await conceptStore.initialize();
    } catch (error) {
        reportError(error, $gettext("Could not load schemes."));
    }

    // Arriving from a concept's own page: look for that concept's matches
    // straight away. The request replaces its own history entry, so going back
    // or reloading never starts the same search twice.
    const conceptId = route.query.concept;
    if (typeof conceptId === "string" && conceptId) {
        await onRun(
            { source_concept_ids: [conceptId] },
            { replaceRoute: true },
        );
        return;
    }

    await loadRuns();
    // The address may already name a run -- a link, or a reload. Only fall back
    // to the newest when it does not.
    if (!(await showNewestRunIfNoneChosen())) {
        await loadCandidates();
    }
}
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

        <Message
            v-if="user && !isEditor"
            :severity="WARN"
            :closable="false"
            class="matches-access-message"
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
                <p class="matches-intro">
                    {{
                        $gettext(
                            "Look for concepts that probably mean the same thing, then dismiss the ones that do not.",
                        )
                    }}
                </p>

                <MatchRunForm
                    :schemes="conceptStore.schemes"
                    :is-starting-run="isCreatingRun"
                    @run="onRun"
                />
            </div>

            <div class="matches-results">
                <div class="matches-results-header">
                    <Select
                        :model-value="activeRunId"
                        :options="runs"
                        option-value="id"
                        :option-label="describeRunOption"
                        :placeholder="$gettext('No runs yet')"
                        :disabled="!runs.length"
                        :aria-label="$gettext('Match run')"
                        class="run-select"
                        @update:model-value="onRunSelected"
                    >
                        <template #value="{ placeholder }">
                            <span>{{
                                activeRunDescription || placeholder
                            }}</span>
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
                            :disabled="!selectedIds.size || isUpdatingSelection"
                            :loading="isUpdatingSelection"
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
                            :disabled="!selectedIds.size || isUpdatingSelection"
                            :loading="isUpdatingSelection"
                            class="action-button"
                            @click="
                                setStatusForSelection(CANDIDATE_STATUS_PENDING)
                            "
                        />
                        <Button
                            v-if="
                                candidateStatus ===
                                    CANDIDATE_STATUS_DISMISSED &&
                                dismissedCount > 0
                            "
                            icon="pi pi-replay"
                            :label="
                                $gettext('Restore all %{count}', {
                                    count: String(dismissedCount),
                                })
                            "
                            :severity="SECONDARY"
                            :outlined="true"
                            :disabled="isChangingAll"
                            :loading="isChangingAll"
                            class="action-button"
                            @click="
                                confirmStatusChangeForAll(
                                    CANDIDATE_STATUS_PENDING,
                                )
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
                            :disabled="isChangingAll"
                            :loading="isChangingAll"
                            class="action-button"
                            @click="
                                confirmStatusChangeForAll(
                                    CANDIDATE_STATUS_DISMISSED,
                                )
                            "
                        />
                        <Button
                            v-if="activeRun?.can_delete"
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

                <Message
                    v-if="hasUnshownResults"
                    :severity="INFO"
                    :closable="false"
                >
                    <span class="unshown-results">
                        {{
                            $gettext(
                                "More pairs have been found. They appear once you refresh, so the list does not move while pairs are selected.",
                            )
                        }}
                        <Button
                            :label="$gettext('Show new results')"
                            size="small"
                            :severity="SECONDARY"
                            :outlined="true"
                            @click="loadCandidates()"
                        />
                    </span>
                </Message>

                <p
                    v-if="!activeRun && !runs.length"
                    class="matches-empty"
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

        <ConfirmDialog group="change-all-matches" />
        <ConfirmDialog group="delete-match-run" />

        <MergeDirectionDialog
            v-if="
                mergingCandidate?.concept_a &&
                mergingCandidate.concept_b &&
                !mergeSurvivor
            "
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

.matches-empty {
    margin: 0;
    color: var(--p-text-muted-color);
}

.unshown-results {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
}

.matches-access-message {
    margin: 1.5rem;
}

@media (max-width: 64rem) {
    .matches-body {
        grid-template-columns: 1fr;
    }
}
</style>
