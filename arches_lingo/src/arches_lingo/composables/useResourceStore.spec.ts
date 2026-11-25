import { describe, expect, it, vi } from "vitest";

vi.mock("@/arches_lingo/api.ts", async (importOriginal) => ({
    ...(await importOriginal<typeof import("@/arches_lingo/api.ts")>()),
    fetchLingoResource: vi.fn(),
    fetchLingoResourcePartial: vi.fn(),
}));

import {
    ResourceNotFoundError,
    fetchLingoResource,
} from "@/arches_lingo/api.ts";
import { createResourceStore } from "@/arches_lingo/composables/useResourceStore.ts";

describe("createResourceStore", () => {
    it("reports a resource the server can't find as not found", async () => {
        vi.mocked(fetchLingoResource).mockRejectedValue(
            new ResourceNotFoundError("Not Found"),
        );

        const store = createResourceStore("concept", "missing-id");
        await store.initialLoad;

        expect(store.isNotFound.value).toBe(true);
    });

    it("doesn't report other failures as not found", async () => {
        vi.mocked(fetchLingoResource).mockRejectedValue(
            new Error("Internal Server Error"),
        );

        const store = createResourceStore("concept", "some-id");
        await store.initialLoad;

        expect(store.error.value?.message).toBe("Internal Server Error");
        expect(store.isNotFound.value).toBe(false);
    });
});
