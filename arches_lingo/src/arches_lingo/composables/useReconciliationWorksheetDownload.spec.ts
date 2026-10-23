import { defineComponent, h } from "vue";

import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { downloadReconciliationWorksheet } from "@/arches_lingo/api.ts";
import { useReconciliationWorksheetDownload } from "@/arches_lingo/composables/useReconciliationWorksheetDownload.ts";
import { saveBlobAsFile } from "@/arches_lingo/utils.ts";

const toastAdd = vi.fn();

vi.mock("primevue/usetoast", () => ({
    useToast: () => ({ add: toastAdd }),
}));

vi.mock("@/arches_lingo/api.ts", () => ({
    downloadReconciliationWorksheet: vi.fn(),
}));

vi.mock("@/arches_lingo/utils.ts", () => ({
    saveBlobAsFile: vi.fn(),
}));

function useDownloadInComponent(): ReturnType<
    typeof useReconciliationWorksheetDownload
> {
    let exposed!: ReturnType<typeof useReconciliationWorksheetDownload>;
    mount(
        defineComponent({
            setup() {
                exposed = useReconciliationWorksheetDownload();
                return () => h("div");
            },
        }),
    );
    return exposed;
}

describe("useReconciliationWorksheetDownload", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        toastAdd.mockReset();
        vi.mocked(saveBlobAsFile).mockReset();
        vi.mocked(downloadReconciliationWorksheet).mockReset();
    });

    it("downloads the worksheet in the selected language and saves it", async () => {
        const worksheet = new Blob(["concept_id\n"]);
        vi.mocked(downloadReconciliationWorksheet).mockResolvedValue(worksheet);
        const { downloadWorksheet, isDownloading } = useDownloadInComponent();

        const isDownloaded = await downloadWorksheet({ scheme_id: "scheme-1" });

        expect(isDownloaded).toBe(true);
        expect(isDownloading.value).toBe(false);
        expect(downloadReconciliationWorksheet).toHaveBeenCalledWith(
            { scheme_id: "scheme-1" },
            expect.any(String),
        );
        expect(vi.mocked(saveBlobAsFile).mock.calls[0][1]).toMatch(
            /^reconciliation-worksheet-\d{4}-\d{2}-\d{2}\.csv$/,
        );
    });

    it("uses a requested file name, adding .csv when it is missing", async () => {
        vi.mocked(downloadReconciliationWorksheet).mockResolvedValue(
            new Blob(),
        );
        const { downloadWorksheet } = useDownloadInComponent();

        await downloadWorksheet({ scheme_id: "scheme-1" }, " aat-terms ");
        await downloadWorksheet({ scheme_id: "scheme-1" }, "aat-terms.CSV");

        expect(
            vi.mocked(saveBlobAsFile).mock.calls.map((call) => call[1]),
        ).toEqual(["aat-terms.csv", "aat-terms.CSV"]);
    });

    it("reports a failed download", async () => {
        vi.mocked(downloadReconciliationWorksheet).mockRejectedValue(
            new Error("That concept set was not found."),
        );
        const { downloadWorksheet } = useDownloadInComponent();

        const isDownloaded = await downloadWorksheet({ concept_set_id: 3 });

        expect(isDownloaded).toBe(false);
        expect(saveBlobAsFile).toHaveBeenCalledTimes(0);
        expect(toastAdd).toHaveBeenCalledWith(
            expect.objectContaining({
                severity: "error",
                detail: "That concept set was not found.",
            }),
        );
    });
});
