import { defineComponent, h } from "vue";

import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
    fetchConceptMatchRun,
    fetchConceptMatchRuns,
} from "@/arches_lingo/api.ts";
import { useConceptMatchRuns } from "@/arches_lingo/components/ConceptMatching/composables/useConceptMatchRuns.ts";
import {
    RUN_POLL_FAILURE_LIMIT,
    RUN_POLL_INTERVAL_MS,
} from "@/arches_lingo/components/ConceptMatching/constants.ts";

import type { ConceptMatchRun } from "@/arches_lingo/types.ts";

const toastAdd = vi.fn();

vi.mock("@/arches_lingo/api.ts", () => ({
    createConceptMatchRun: vi.fn(),
    fetchConceptMatchRun: vi.fn(),
    fetchConceptMatchRuns: vi.fn(),
}));

vi.mock("primevue/usetoast", () => ({
    useToast: () => ({ add: toastAdd }),
}));

vi.mock("vue3-gettext", () => ({
    useGettext: () => ({
        $gettext: (text: string) => text,
        $ngettext: (singular: string) => singular,
    }),
}));

const mockedFetchRun = vi.mocked(fetchConceptMatchRun);
const mockedFetchRuns = vi.mocked(fetchConceptMatchRuns);

function matchRun(overrides: Partial<ConceptMatchRun> = {}): ConceptMatchRun {
    return {
        id: 1,
        status: "running",
        candidate_count: 0,
        started_by_viewer: true,
        ...overrides,
    } as ConceptMatchRun;
}

function mountRuns(activeRunId: number | null) {
    let exposed!: ReturnType<typeof useConceptMatchRuns>;
    const wrapper = mount(
        defineComponent({
            setup() {
                exposed = useConceptMatchRuns({ activeRunId });
                return () => h("div");
            },
        }),
    );
    return { wrapper, runs: exposed };
}

async function advanceOnePoll(): Promise<void> {
    await vi.advanceTimersByTimeAsync(RUN_POLL_INTERVAL_MS);
    await flushPromises();
}

describe("useConceptMatchRuns", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        toastAdd.mockReset();
        mockedFetchRun.mockReset();
        mockedFetchRuns.mockReset();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("polls the run on screen until it finishes", async () => {
        mockedFetchRuns.mockResolvedValue({ data: [matchRun()] });
        mockedFetchRun
            .mockResolvedValueOnce(matchRun({ candidate_count: 3 }))
            .mockResolvedValueOnce(
                matchRun({ status: "complete", candidate_count: 5 }),
            );
        const { runs } = mountRuns(1);
        await runs.loadRuns();
        await flushPromises();

        await advanceOnePoll();
        expect(runs.activeRun.value?.candidate_count).toBe(3);
        expect(runs.activeRunIsUnfinished.value).toBe(true);

        await advanceOnePoll();
        expect(runs.activeRun.value?.candidate_count).toBe(5);
        expect(runs.activeRunIsUnfinished.value).toBe(false);
        expect(toastAdd).toHaveBeenCalledTimes(1);

        await advanceOnePoll();
        expect(mockedFetchRun).toHaveBeenCalledTimes(2);
    });

    it("stops and reloads the list when the run has been deleted", async () => {
        mockedFetchRuns
            .mockResolvedValueOnce({ data: [matchRun()] })
            .mockResolvedValueOnce({ data: [] });
        mockedFetchRun.mockResolvedValueOnce(null);
        const { runs } = mountRuns(1);
        await runs.loadRuns();
        await flushPromises();

        await advanceOnePoll();

        expect(runs.runs.value).toEqual([]);
        await advanceOnePoll();
        expect(mockedFetchRun).toHaveBeenCalledTimes(1);
    });

    it("gives up after repeated failures and says so", async () => {
        mockedFetchRuns.mockResolvedValue({ data: [matchRun()] });
        mockedFetchRun.mockRejectedValue(new Error("Network down"));
        const { runs } = mountRuns(1);
        await runs.loadRuns();
        await flushPromises();

        for (let attempt = 0; attempt < RUN_POLL_FAILURE_LIMIT + 2; attempt++) {
            await advanceOnePoll();
        }

        expect(mockedFetchRun).toHaveBeenCalledTimes(RUN_POLL_FAILURE_LIMIT);
        expect(toastAdd).toHaveBeenCalledTimes(1);
    });

    it("does not poll a run that has finished", async () => {
        mockedFetchRuns.mockResolvedValue({
            data: [matchRun({ status: "complete" })],
        });
        const { runs } = mountRuns(1);
        await runs.loadRuns();

        await advanceOnePoll();

        expect(mockedFetchRun).toHaveBeenCalledTimes(0);
    });

    it("defaults to the viewer's own newest run", async () => {
        mockedFetchRuns.mockResolvedValue({
            data: [
                matchRun({ id: 3, started_by_viewer: false }),
                matchRun({ id: 2, started_by_viewer: true }),
            ],
        });
        const { runs } = mountRuns(null);
        await runs.loadRuns();

        expect(runs.newestRunId()).toBe(2);
    });
});
