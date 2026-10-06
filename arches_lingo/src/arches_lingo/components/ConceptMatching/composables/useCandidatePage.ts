import { ref } from "vue";

import { fetchConceptMatchCandidates } from "@/arches_lingo/api.ts";
import { CANDIDATES_PER_PAGE } from "@/arches_lingo/components/ConceptMatching/constants.ts";

import type { Ref } from "vue";
import type {
    ConceptMatchCandidate,
    ConceptMatchCandidateStatus,
} from "@/arches_lingo/types.ts";
import type { CandidateSelectionChange } from "@/arches_lingo/components/ConceptMatching/types.ts";

export function useCandidatePage({
    activeRunId,
    candidateStatus,
    pageNumber,
}: {
    activeRunId: number | null;
    candidateStatus: Ref<ConceptMatchCandidateStatus>;
    pageNumber: Ref<number>;
}): {
    candidates: Ref<ConceptMatchCandidate[]>;
    totalResults: Ref<number>;
    isLoadingCandidates: Ref<boolean>;
    loadError: Ref<string | null>;
    hasUnshownResults: Ref<boolean>;
    lastPageWhenPastEnd: Ref<number | null>;
    selectedIds: Ref<Set<number>>;
    loadCandidates: (options?: { quiet?: boolean }) => Promise<void>;
    changeSelection: (change: CandidateSelectionChange) => void;
    selectAllOnPage: (isSelected: boolean) => void;
    clearSelection: () => void;
} {
    const candidates = ref<ConceptMatchCandidate[]>([]);
    const totalResults = ref(0);
    const isLoadingCandidates = ref(false);
    const loadError = ref<string | null>(null);
    // While pairs are selected, a refresh would move rows under the reviewer,
    // so new results wait until they ask for them.
    const hasUnshownResults = ref(false);
    // Set when the page asked for no longer exists -- the queue shrank under a
    // bookmark, say -- so the caller can move to the last one that does.
    const lastPageWhenPastEnd = ref<number | null>(null);
    const selectedIds = ref<Set<number>>(new Set());

    // Only the newest response is shown, whatever order responses arrive in.
    let latestRequest = 0;
    let loadingRequest = 0;

    async function loadCandidates({ quiet = false } = {}): Promise<void> {
        if (activeRunId === null) {
            candidates.value = [];
            totalResults.value = 0;
            return;
        }
        if (quiet && selectedIds.value.size) {
            hasUnshownResults.value = true;
            return;
        }

        const requestNumber = ++latestRequest;
        // A poll refreshes in place; only a refresh the reviewer asked for
        // shows the loading state.
        if (!quiet) {
            isLoadingCandidates.value = true;
            loadingRequest = requestNumber;
            hasUnshownResults.value = false;
        }
        loadError.value = null;
        const requestedPageNumber = pageNumber.value;
        try {
            const page = await fetchConceptMatchCandidates(
                activeRunId,
                candidateStatus.value,
                requestedPageNumber,
                CANDIDATES_PER_PAGE,
            );
            if (requestNumber !== latestRequest) return;

            const lastPageNumber = Math.max(
                1,
                Math.ceil(page.total_results / CANDIDATES_PER_PAGE),
            );
            if (!page.data.length && requestedPageNumber > lastPageNumber) {
                lastPageWhenPastEnd.value = lastPageNumber;
                return;
            }
            lastPageWhenPastEnd.value = null;
            candidates.value = page.data;
            totalResults.value = page.total_results;
        } catch (error) {
            if (requestNumber === latestRequest) {
                loadError.value =
                    error instanceof Error ? error.message : String(error);
            }
        } finally {
            if (loadingRequest === requestNumber) {
                isLoadingCandidates.value = false;
            }
        }
    }

    function changeSelection({
        candidateId,
        isSelected,
    }: CandidateSelectionChange): void {
        const updatedSelection = new Set(selectedIds.value);
        if (isSelected) {
            updatedSelection.add(candidateId);
        } else {
            updatedSelection.delete(candidateId);
        }
        selectedIds.value = updatedSelection;
    }

    function selectAllOnPage(isSelected: boolean): void {
        const updatedSelection = new Set(selectedIds.value);
        for (const candidate of candidates.value) {
            if (isSelected) {
                updatedSelection.add(candidate.id);
            } else {
                updatedSelection.delete(candidate.id);
            }
        }
        selectedIds.value = updatedSelection;
    }

    function clearSelection(): void {
        selectedIds.value = new Set();
    }

    return {
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
    };
}
