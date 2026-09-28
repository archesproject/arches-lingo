import { defineComponent, h } from "vue";

import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it, vi } from "vitest";

import { useMatchReviewRoute } from "@/arches_lingo/components/ConceptMatching/composables/useMatchReviewRoute.ts";

async function mountAt(path: string) {
    const router = createRouter({
        history: createMemoryHistory(),
        routes: [
            {
                path: "/concept-matches/:runId?",
                name: "concept-matches",
                component: { render: () => null },
            },
        ],
    });
    await router.push(path);
    await router.isReady();

    const onViewChanged = vi.fn();
    let exposed!: ReturnType<typeof useMatchReviewRoute>;
    mount(
        defineComponent({
            setup() {
                exposed = useMatchReviewRoute(onViewChanged);
                return () => h("div");
            },
        }),
        { global: { plugins: [router] } },
    );
    return { router, route: exposed, onViewChanged };
}

describe("useMatchReviewRoute", () => {
    it("reads the run, page and queue from the address", async () => {
        const { route } = await mountAt(
            "/concept-matches/12?page=3&status=dismissed",
        );

        expect(route.activeRunId.value).toBe(12);
        expect(route.pageNumber.value).toBe(3);
        expect(route.candidateStatus.value).toBe("dismissed");
    });

    it("falls back to the outstanding queue for a status it does not offer", async () => {
        const { route } = await mountAt("/concept-matches/12?status=maybe");

        expect(route.candidateStatus.value).toBe("pending");
    });

    it("writes down only what differs from the default view", async () => {
        const { router, route } = await mountAt("/concept-matches/12?page=3");

        await route.showView({ pageNumber: 1, status: "pending" });

        expect(router.currentRoute.value.fullPath).toBe("/concept-matches/12");
    });

    it("reports whether the run or queue changed", async () => {
        const { route, onViewChanged } = await mountAt("/concept-matches/12");

        await route.showView({ pageNumber: 2 });
        await flushPromises();
        expect(onViewChanged).toHaveBeenLastCalledWith({
            runChanged: false,
            statusChanged: false,
        });

        await route.showView({ runId: 13, pageNumber: 1 });
        await flushPromises();
        expect(onViewChanged).toHaveBeenLastCalledWith({
            runChanged: true,
            statusChanged: false,
        });
    });

    it("hands over the concept a search was started from", async () => {
        const { route } = await mountAt("/concept-matches?concept=abc");

        expect(route.conceptIdToSearchFrom()).toBe("abc");
    });
});
