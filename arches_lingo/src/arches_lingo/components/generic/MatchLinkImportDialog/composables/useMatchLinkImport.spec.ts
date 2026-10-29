import { defineComponent, h } from "vue";

import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
    fetchMatchLinkImport,
    previewMatchLinkImport,
    startMatchLinkImport,
} from "@/arches_lingo/api.ts";
import { useMatchLinkImport } from "@/arches_lingo/components/generic/MatchLinkImportDialog/composables/useMatchLinkImport.ts";
import {
    MATCH_LINK_IMPORT_MAX_FAILED_POLLS,
    MATCH_LINK_IMPORT_POLL_INTERVAL_MS,
} from "@/arches_lingo/components/generic/MatchLinkImportDialog/utils.ts";

import type { MatchLinkImportRecord } from "@/arches_lingo/components/generic/MatchLinkImportDialog/types.ts";

const toastAdd = vi.fn();

vi.mock("primevue/usetoast", () => ({
    useToast: () => ({ add: toastAdd }),
}));

vi.mock("@/arches_lingo/api.ts", () => ({
    fetchMatchLinkImport: vi.fn(),
    previewMatchLinkImport: vi.fn(),
    startMatchLinkImport: vi.fn(),
}));

const UPLOADED_FILE = new File(["concept_id,match_uri"], "matches.csv");

function importRecord(
    overrides: Partial<MatchLinkImportRecord>,
): MatchLinkImportRecord {
    return {
        id: 7,
        filename: "matches.csv",
        status: "pending",
        scheme_id: null,
        created: "2026-10-23T10:00:00Z",
        finished: null,
        total_links: 1,
        outcome_counts: {},
        error_message: "",
        ...overrides,
    };
}

async function useImportWithFile(): Promise<
    ReturnType<typeof useMatchLinkImport>
> {
    let exposed!: ReturnType<typeof useMatchLinkImport>;
    mount(
        defineComponent({
            setup() {
                exposed = useMatchLinkImport();
                return () => h("div");
            },
        }),
    );
    await exposed.previewFile(UPLOADED_FILE);
    return exposed;
}

describe("useMatchLinkImport", () => {
    beforeEach(() => {
        toastAdd.mockReset();
        vi.mocked(previewMatchLinkImport).mockReset();
        vi.mocked(startMatchLinkImport).mockReset();
        vi.mocked(fetchMatchLinkImport).mockReset();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("keeps polling through a lost status check, then gives up without calling the import failed", async () => {
        vi.useFakeTimers();
        vi.mocked(startMatchLinkImport).mockResolvedValue(importRecord({}));
        vi.mocked(fetchMatchLinkImport)
            .mockRejectedValueOnce(new Error("Bad Gateway"))
            .mockResolvedValueOnce(importRecord({ status: "running" }))
            .mockRejectedValue(new Error("Bad Gateway"));
        const { applyImport, isApplying } = await useImportWithFile();

        const applying = applyImport();
        await vi.advanceTimersByTimeAsync(
            MATCH_LINK_IMPORT_POLL_INTERVAL_MS *
                (MATCH_LINK_IMPORT_MAX_FAILED_POLLS + 2),
        );
        await applying;

        expect(fetchMatchLinkImport).toHaveBeenCalledTimes(
            MATCH_LINK_IMPORT_MAX_FAILED_POLLS + 2,
        );
        expect(isApplying.value).toBe(false);
        expect(toastAdd).toHaveBeenCalledTimes(1);
        expect(toastAdd).toHaveBeenCalledWith(
            expect.objectContaining({
                severity: "warn",
                summary: "Unable to check on the match link import",
            }),
        );
    });

    it("reports an import that failed on the server", async () => {
        vi.mocked(startMatchLinkImport).mockResolvedValue(
            importRecord({ status: "failed", error_message: "Worker died" }),
        );
        const { applyImport, finishedImport } = await useImportWithFile();

        await applyImport();

        expect(finishedImport.value).toBeNull();
        expect(toastAdd).toHaveBeenCalledWith(
            expect.objectContaining({
                severity: "error",
                detail: "Worker died",
            }),
        );
    });

    it("reports a request that could not be sent", async () => {
        vi.mocked(startMatchLinkImport).mockRejectedValue(new Error("Offline"));
        const { applyImport } = await useImportWithFile();

        await applyImport();
        await flushPromises();

        expect(toastAdd).toHaveBeenCalledWith(
            expect.objectContaining({ severity: "error", detail: "Offline" }),
        );
    });
});
