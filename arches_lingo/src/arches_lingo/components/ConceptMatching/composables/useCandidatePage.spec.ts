import { ref } from "vue";

import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchConceptMatchCandidates } from "@/arches_lingo/api.ts";
import { useCandidatePage } from "@/arches_lingo/components/ConceptMatching/composables/useCandidatePage.ts";

import type {
    ConceptMatchCandidate,
    ConceptMatchCandidateStatus,
    ConceptMatchCandidatePage,
} from "@/arches_lingo/types.ts";

vi.mock("@/arches_lingo/api.ts", () => ({
    fetchConceptMatchCandidates: vi.fn(),
}));

const mockedFetch = vi.mocked(fetchConceptMatchCandidates);

function candidatePage(
    candidateIds: number[],
    totalResults = candidateIds.length,
): ConceptMatchCandidatePage {
    return {
        data: candidateIds.map((id) => ({ id }) as ConceptMatchCandidate),
        total_results: totalResults,
        current_page: 1,
        items_per_page: 50,
    };
}

function deferred<ValueType>(): {
    promise: Promise<ValueType>;
    resolve: (value: ValueType) => void;
} {
    let resolve!: (value: ValueType) => void;
    const promise = new Promise<ValueType>((resolvePromise) => {
        resolve = resolvePromise;
    });
    return { promise, resolve };
}

function setUpPage(pageNumber = 1): ReturnType<typeof useCandidatePage> {
    return useCandidatePage({
        activeRunId: 7,
        candidateStatus: ref<ConceptMatchCandidateStatus>("pending"),
        pageNumber: ref(pageNumber),
    });
}

describe("useCandidatePage", () => {
    beforeEach(() => {
        mockedFetch.mockReset();
    });

    it("shows only the newest response when two overlap", async () => {
        const slowResponse = deferred<ConceptMatchCandidatePage>();
        mockedFetch
            .mockReturnValueOnce(slowResponse.promise)
            .mockResolvedValueOnce(candidatePage([2]));
        const { candidates, isLoadingCandidates, loadCandidates } = setUpPage();

        const olderLoad = loadCandidates();
        await loadCandidates();
        slowResponse.resolve(candidatePage([1]));
        await olderLoad;

        expect(candidates.value.map((candidate) => candidate.id)).toEqual([2]);
        expect(isLoadingCandidates.value).toBe(false);
    });

    it("holds back a quiet refresh while pairs are selected", async () => {
        const { hasUnshownResults, loadCandidates, changeSelection } =
            setUpPage();
        changeSelection({ candidateId: 1, isSelected: true });

        await loadCandidates({ quiet: true });

        expect(mockedFetch).toHaveBeenCalledTimes(0);
        expect(hasUnshownResults.value).toBe(true);

        mockedFetch.mockResolvedValueOnce(candidatePage([1]));
        await loadCandidates();
        expect(hasUnshownResults.value).toBe(false);
    });

    it("names the last page when asked for one past the end", async () => {
        mockedFetch.mockResolvedValueOnce(candidatePage([], 60));
        const { lastPageWhenPastEnd, loadCandidates } = setUpPage(4);

        await loadCandidates();

        expect(lastPageWhenPastEnd.value).toBe(2);
    });

    it("keeps an error for the newest request", async () => {
        mockedFetch.mockRejectedValueOnce(new Error("Server unavailable"));
        const { loadError, loadCandidates } = setUpPage();

        await loadCandidates();

        expect(loadError.value).toBe("Server unavailable");
    });

    it("selects and clears everything on the page", async () => {
        mockedFetch.mockResolvedValueOnce(candidatePage([1, 2]));
        const { selectedIds, loadCandidates, selectAllOnPage, clearSelection } =
            setUpPage();
        await loadCandidates();

        selectAllOnPage(true);
        expect([...selectedIds.value]).toEqual([1, 2]);

        selectAllOnPage(false);
        expect(selectedIds.value.size).toBe(0);

        selectAllOnPage(true);
        clearSelection();
        expect(selectedIds.value.size).toBe(0);
    });
});
