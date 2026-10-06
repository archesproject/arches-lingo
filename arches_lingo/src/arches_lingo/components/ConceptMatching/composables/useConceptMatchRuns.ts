import { computed, onBeforeUnmount, ref, watch } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import {
    createConceptMatchRun,
    fetchConceptMatchRun,
    fetchConceptMatchRuns,
} from "@/arches_lingo/api.ts";
import {
    RUN_POLL_FAILURE_LIMIT,
    RUN_POLL_INTERVAL_MS,
    RUN_STATUS_FAILED,
} from "@/arches_lingo/components/ConceptMatching/constants.ts";
import { useErrorToast } from "@/arches_lingo/components/ConceptMatching/composables/useErrorToast.ts";
import { isRunUnfinished } from "@/arches_lingo/components/ConceptMatching/utils.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    ERROR,
    SUCCESS,
} from "@/arches_lingo/constants.ts";

import type { ComputedRef, Ref } from "vue";
import type {
    ConceptMatchRun,
    ConceptMatchRunRequest,
} from "@/arches_lingo/types.ts";

/**
 * The runs every editor can see, and the one on screen, which is polled while
 * it is unfinished however the reviewer got to it.
 */
export function useConceptMatchRuns({
    activeRunId,
}: {
    activeRunId: number | null;
}): {
    runs: Ref<ConceptMatchRun[]>;
    activeRun: ComputedRef<ConceptMatchRun | undefined>;
    activeRunIsUnfinished: ComputedRef<boolean>;
    isCreatingRun: Ref<boolean>;
    loadRuns: () => Promise<void>;
    newestRunId: () => number | null;
    createRun: (
        request: ConceptMatchRunRequest,
    ) => Promise<ConceptMatchRun | null>;
} {
    const { $gettext, $ngettext } = useGettext();
    const toast = useToast();
    const { reportError } = useErrorToast();

    const runs = ref<ConceptMatchRun[]>([]);
    const isCreatingRun = ref(false);

    let pollTimer: ReturnType<typeof setInterval> | undefined;
    let isPollInFlight = false;
    let consecutivePollFailures = 0;
    let latestRunsRequest = 0;

    const activeRun = computed(() =>
        runs.value.find((run) => run.id === activeRunId),
    );

    const activeRunIsUnfinished = computed(() =>
        Boolean(activeRun.value && isRunUnfinished(activeRun.value)),
    );

    watch(activeRunIsUnfinished, function (isUnfinished) {
        if (isUnfinished && activeRunId !== null) {
            pollUntilFinished(activeRunId);
            return;
        }
        stopPolling();
    });

    onBeforeUnmount(stopPolling);

    async function loadRuns(): Promise<void> {
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
    function newestRunId(): number | null {
        const newestOwnRun = runs.value.find((run) => run.started_by_viewer);
        return (newestOwnRun ?? runs.value[0])?.id ?? null;
    }

    async function createRun(
        request: ConceptMatchRunRequest,
    ): Promise<ConceptMatchRun | null> {
        isCreatingRun.value = true;
        try {
            const run = await createConceptMatchRun(request);
            await loadRuns();
            if (!isRunUnfinished(run)) {
                reportRunFinished(run);
            }
            return run;
        } catch (error) {
            reportError(error, $gettext("Could not detect matches."));
            return null;
        } finally {
            isCreatingRun.value = false;
        }
    }

    function stopPolling(): void {
        if (pollTimer !== undefined) {
            clearInterval(pollTimer);
            pollTimer = undefined;
        }
    }

    function pollUntilFinished(runId: number): void {
        stopPolling();
        consecutivePollFailures = 0;
        pollTimer = setInterval(() => pollOnce(runId), RUN_POLL_INTERVAL_MS);
    }

    async function pollOnce(runId: number): Promise<void> {
        // A tick still in flight is skipped rather than queued behind itself.
        if (isPollInFlight) return;
        isPollInFlight = true;
        try {
            const run = await fetchConceptMatchRun(runId);
            consecutivePollFailures = 0;
            if (!run) {
                // Cancelled, from here or from somewhere else.
                stopPolling();
                await loadRuns();
                return;
            }
            runs.value = runs.value.map((listedRun) =>
                listedRun.id === runId ? run : listedRun,
            );
            if (isRunUnfinished(run)) return;
            stopPolling();
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
    }

    function reportRunFinished(run: ConceptMatchRun): void {
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

    return {
        runs,
        activeRun,
        activeRunIsUnfinished,
        isCreatingRun,
        loadRuns,
        newestRunId,
        createRun,
    };
}
