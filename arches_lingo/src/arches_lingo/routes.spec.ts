import { beforeEach, describe, expect, it, vi } from "vitest";

import { createMemoryHistory, createRouter } from "vue-router";

vi.mock("@/arches_lingo/api.ts", () => ({
    resolveSchemeIdentifier: vi.fn(),
    resolveConceptIdentifier: vi.fn(),
}));

import {
    resolveConceptIdentifier,
    resolveSchemeIdentifier,
} from "@/arches_lingo/api.ts";
import { routeNames, routes } from "@/arches_lingo/routes.ts";

describe("unknown identifiers", () => {
    beforeEach(() => {
        vi.mocked(resolveSchemeIdentifier).mockResolvedValue(null);
        vi.mocked(resolveConceptIdentifier).mockResolvedValue(null);
    });

    it.each([
        "/schemes/missing?tab=notes",
        "/schemes/aat/concepts/missing?tab=notes#labels",
    ])(
        "show the not-found page at the URL the user followed: %s",
        async (url) => {
            const router = createRouter({
                history: createMemoryHistory(),
                routes,
            });

            await router.push(url);

            expect(router.currentRoute.value.name).toBe(routeNames.notFound);
            expect(router.currentRoute.value.fullPath).toBe(url);
        },
    );
});
