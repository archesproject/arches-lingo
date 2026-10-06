import { computed } from "vue";

import { useRoute, useRouter } from "vue-router";

import { routeNames } from "@/arches_lingo/routes.ts";
import { CANDIDATE_STATUS_PENDING } from "@/arches_lingo/components/ConceptMatching/constants.ts";
import { candidateStatusFromRoute } from "@/arches_lingo/components/ConceptMatching/utils.ts";

import type { ComputedRef } from "vue";
import type { RouteLocationRaw } from "vue-router";
import type { ConceptMatchCandidateStatus } from "@/arches_lingo/types.ts";

interface MatchReviewView {
    runId?: number | null;
    pageNumber?: number;
    status?: ConceptMatchCandidateStatus;
}

/**
 * Which run, page and queue are shown lives in the address, so back and forward
 * move between them and a queue can be sent to someone else. The address is
 * the one source of truth: a click and the back button arrive by the same path.
 *
 * The run is part of the path, which the app keys its RouterView on, so showing
 * another run mounts a new page; only the page and queue change underneath one.
 */
export function useMatchReviewRoute(): {
    activeRunId: number | null;
    candidateStatus: ComputedRef<ConceptMatchCandidateStatus>;
    pageNumber: ComputedRef<number>;
    conceptIdToSearchFrom: () => string | null;
    showView: (
        view: MatchReviewView,
        options?: { replace?: boolean },
    ) => Promise<unknown>;
} {
    const route = useRoute();
    const router = useRouter();

    const activeRunId = runIdInRoute();
    const candidateStatus = computed(() =>
        candidateStatusFromRoute(route.query.status),
    );
    const pageNumber = computed(pageNumberInRoute);

    function runIdInRoute(): number | null {
        const rawRunId = Array.isArray(route.params.runId)
            ? route.params.runId[0]
            : route.params.runId;
        const runId = Number(rawRunId);
        return rawRunId && Number.isInteger(runId) && runId > 0 ? runId : null;
    }

    function pageNumberInRoute(): number {
        const routePageNumber = Number(route.query.page);
        return Number.isInteger(routePageNumber) && routePageNumber > 0
            ? routePageNumber
            : 1;
    }

    function conceptIdToSearchFrom(): string | null {
        const conceptId = route.query.concept;
        return typeof conceptId === "string" && conceptId ? conceptId : null;
    }

    // Only what differs from the default is written down, so the ordinary case
    // -- the first page of a run's outstanding pairs -- stays a plain link.
    function routeForView({
        runId = activeRunId,
        pageNumber: viewPageNumber = pageNumber.value,
        status = candidateStatus.value,
    }: MatchReviewView): RouteLocationRaw {
        const query: Record<string, string> = {};
        if (viewPageNumber > 1) {
            query.page = String(viewPageNumber);
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

    function showView(
        view: MatchReviewView,
        { replace = false }: { replace?: boolean } = {},
    ): Promise<unknown> {
        const location = routeForView(view);
        return replace ? router.replace(location) : router.push(location);
    }

    return {
        activeRunId,
        candidateStatus,
        pageNumber,
        conceptIdToSearchFrom,
        showView,
    };
}
