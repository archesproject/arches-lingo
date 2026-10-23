import { defineComponent, h } from "vue";

import { flushPromises, mount } from "@vue/test-utils";
import PrimeVue from "primevue/config";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import MatchLinkImportDialog from "@/arches_lingo/components/generic/MatchLinkImportDialog/MatchLinkImportDialog.vue";
import MatchLinkImportPreview from "@/arches_lingo/components/generic/MatchLinkImportDialog/components/MatchLinkImportPreview.vue";
import MatchLinkImportUpload from "@/arches_lingo/components/generic/MatchLinkImportDialog/components/MatchLinkImportUpload.vue";

import {
    fetchMatchLinkImport,
    previewMatchLinkImport,
    startMatchLinkImport,
} from "@/arches_lingo/api.ts";
import { MATCH_LINK_IMPORT_POLL_INTERVAL_MS } from "@/arches_lingo/components/generic/MatchLinkImportDialog/utils.ts";

import type { VueWrapper } from "@vue/test-utils";
import type {
    MatchLinkImportOutcome,
    MatchLinkImportPreview as MatchLinkImportPreviewData,
    MatchLinkImportRecord,
} from "@/arches_lingo/types.ts";

const toastAdd = vi.fn();

vi.mock("primevue/usetoast", () => ({
    useToast: () => ({ add: toastAdd }),
}));

vi.mock("vue3-gettext", () => {
    const interpolate = (text: string, params: Record<string, string> = {}) =>
        text.replace(/%\{(\w+)\}/g, (_match, key) => params[key] ?? "");
    return {
        useGettext: () => ({
            $gettext: interpolate,
            $ngettext: (
                singular: string,
                plural: string,
                count: number,
                params?: Record<string, string>,
            ) => interpolate(count === 1 ? singular : plural, params),
        }),
    };
});

vi.mock("@/arches_lingo/api.ts", () => ({
    fetchMatchLinkImport: vi.fn(),
    previewMatchLinkImport: vi.fn(),
    startMatchLinkImport: vi.fn(),
}));

const UPLOADED_FILE = new File(["concept_id,match_uri"], "matches.csv");

// PrimeVue's Dialog renders into a portal; render its slots in place instead.
const DialogStub = defineComponent({
    setup(_props, { slots }) {
        return () => h("div", [slots.default?.(), slots.footer?.()]);
    },
});

function previewWith(
    countsByOutcome: MatchLinkImportPreviewData["counts_by_outcome"],
): MatchLinkImportPreviewData {
    return {
        total_rows: 2,
        counts_by_outcome: countsByOutcome,
        rows: [
            {
                row_number: 2,
                concept_id: "concept-1",
                concept_label: "Vases",
                match_uri: "http://www.wikidata.org/entity/Q191851",
                match_type: "exactMatch",
                outcome: "add",
                is_internal_concept: false,
            },
            {
                row_number: 3,
                concept_id: "concept-2",
                concept_label: "Jars",
                match_uri: "http://www.wikidata.org/entity/Q2413314",
                match_type: "exactMatch",
                outcome: "already_linked",
                is_internal_concept: true,
            },
        ],
    };
}

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
        total_rows: 2,
        outcome_counts: {},
        error_message: "",
        ...overrides,
    };
}

function mountDialog(schemeId?: string): VueWrapper {
    return mount(MatchLinkImportDialog, {
        props: { schemeId },
        global: {
            plugins: [PrimeVue],
            stubs: { Dialog: DialogStub },
        },
    });
}

async function selectFile(wrapper: VueWrapper): Promise<void> {
    wrapper
        .findComponent(MatchLinkImportUpload)
        .vm.$emit("file-selected", UPLOADED_FILE);
    await flushPromises();
}

function addLinksButton(wrapper: VueWrapper) {
    return wrapper
        .findAll("button")
        .find((button) => button.text().startsWith("Add"))!;
}

describe("MatchLinkImportDialog", () => {
    beforeEach(() => {
        // jsdom has no matchMedia, which PrimeVue's Select listens to.
        window.matchMedia = vi.fn().mockReturnValue({
            matches: false,
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
        });
        toastAdd.mockReset();
        vi.mocked(previewMatchLinkImport).mockReset();
        vi.mocked(startMatchLinkImport).mockReset();
        vi.mocked(fetchMatchLinkImport).mockReset();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("previews the chosen file and offers to add its new links", async () => {
        vi.mocked(previewMatchLinkImport).mockResolvedValue(
            previewWith({ add: 1, already_linked: 1 }),
        );
        const wrapper = mountDialog();

        await selectFile(wrapper);

        expect(previewMatchLinkImport).toHaveBeenCalledWith(
            UPLOADED_FILE,
            undefined,
        );
        expect(wrapper.findComponent(MatchLinkImportPreview).exists()).toBe(
            true,
        );
        expect(addLinksButton(wrapper).attributes("disabled")).toBeUndefined();
        expect(addLinksButton(wrapper).text()).toBe("Add 1 link");
        expect(wrapper.find('[role="status"]').text()).toBe("2 rows checked");
    });

    it("cannot apply a file with nothing to add", async () => {
        vi.mocked(previewMatchLinkImport).mockResolvedValue(
            previewWith({ already_linked: 2 }),
        );
        const wrapper = mountDialog();

        await selectFile(wrapper);

        expect(addLinksButton(wrapper).attributes("disabled")).toBeDefined();
    });

    it("reports a file the server cannot read", async () => {
        vi.mocked(previewMatchLinkImport).mockRejectedValue(
            new Error("The file needs these columns: match_uri."),
        );
        const wrapper = mountDialog();

        await selectFile(wrapper);

        expect(toastAdd).toHaveBeenCalledWith(
            expect.objectContaining({
                severity: "error",
                detail: "The file needs these columns: match_uri.",
            }),
        );
        expect(wrapper.findComponent(MatchLinkImportPreview).exists()).toBe(
            false,
        );
    });

    it("applies the import, waits for it, and reports the result", async () => {
        vi.useFakeTimers();
        vi.mocked(previewMatchLinkImport).mockResolvedValue(
            previewWith({ add: 1, already_linked: 1 }),
        );
        vi.mocked(startMatchLinkImport).mockResolvedValue(importRecord({}));
        vi.mocked(fetchMatchLinkImport)
            .mockResolvedValueOnce(importRecord({ status: "running" }))
            .mockResolvedValueOnce(
                importRecord({
                    status: "complete",
                    outcome_counts: { add: 1, already_linked: 1 },
                }),
            );
        const wrapper = mountDialog();
        await selectFile(wrapper);

        await addLinksButton(wrapper).trigger("click");
        await vi.advanceTimersByTimeAsync(
            MATCH_LINK_IMPORT_POLL_INTERVAL_MS * 2,
        );
        await flushPromises();

        expect(fetchMatchLinkImport).toHaveBeenCalledTimes(2);
        expect(toastAdd).toHaveBeenCalledWith(
            expect.objectContaining({
                severity: "success",
                summary: "1 match link added",
            }),
        );
        expect(wrapper.text()).toContain("Already linked: 1");
        expect(wrapper.find('[role="status"]').text()).toBe("Import finished.");
    });

    it("reports an import that failed on the server", async () => {
        vi.mocked(previewMatchLinkImport).mockResolvedValue(
            previewWith({ add: 1 }),
        );
        vi.mocked(startMatchLinkImport).mockResolvedValue(
            importRecord({ status: "failed", error_message: "Worker died" }),
        );
        const wrapper = mountDialog();
        await selectFile(wrapper);

        await addLinksButton(wrapper).trigger("click");
        await flushPromises();

        expect(toastAdd).toHaveBeenCalledWith(
            expect.objectContaining({
                severity: "error",
                detail: "Worker died",
            }),
        );
    });

    it("reports a request that could not be sent", async () => {
        vi.mocked(previewMatchLinkImport).mockResolvedValue(
            previewWith({ add: 1 }),
        );
        vi.mocked(startMatchLinkImport).mockRejectedValue(new Error("Offline"));
        const wrapper = mountDialog();
        await selectFile(wrapper);

        await addLinksButton(wrapper).trigger("click");
        await flushPromises();

        expect(toastAdd).toHaveBeenCalledWith(
            expect.objectContaining({ severity: "error", detail: "Offline" }),
        );
    });

    it("limits an import opened from a scheme to that scheme", async () => {
        vi.mocked(previewMatchLinkImport).mockResolvedValue(
            previewWith({ add: 1 }),
        );
        vi.mocked(startMatchLinkImport).mockResolvedValue(
            importRecord({ status: "complete", scheme_id: "scheme-1" }),
        );
        const wrapper = mountDialog("scheme-1");
        await selectFile(wrapper);

        await addLinksButton(wrapper).trigger("click");
        await flushPromises();

        expect(wrapper.text()).toContain(
            "Only concepts in this scheme receive links.",
        );
        expect(previewMatchLinkImport).toHaveBeenCalledWith(
            UPLOADED_FILE,
            "scheme-1",
        );
        expect(startMatchLinkImport).toHaveBeenCalledWith(
            UPLOADED_FILE,
            "scheme-1",
        );
    });

    it("can be closed while an import runs, and stops polling", async () => {
        vi.useFakeTimers();
        vi.mocked(previewMatchLinkImport).mockResolvedValue(
            previewWith({ add: 1 }),
        );
        vi.mocked(startMatchLinkImport).mockResolvedValue(importRecord({}));
        const wrapper = mountDialog();
        await selectFile(wrapper);
        await addLinksButton(wrapper).trigger("click");

        await wrapper
            .findAll("button")
            .find((button) => button.text() === "Close")!
            .trigger("click");
        expect(wrapper.emitted("close")).toHaveLength(1);
        wrapper.unmount();
        await vi.advanceTimersByTimeAsync(MATCH_LINK_IMPORT_POLL_INTERVAL_MS);

        expect(toastAdd).toHaveBeenCalledWith(
            expect.objectContaining({ severity: "info" }),
        );
        expect(fetchMatchLinkImport).toHaveBeenCalledTimes(0);
    });

    it("closes when cancelled", async () => {
        const wrapper = mountDialog();

        await wrapper
            .findAll("button")
            .find((button) => button.text() === "Cancel")!
            .trigger("click");

        expect(wrapper.emitted("close")).toHaveLength(1);
    });

    it("filters the preview rows by outcome", async () => {
        const preview = mount(MatchLinkImportPreview, {
            props: { preview: previewWith({ add: 1, already_linked: 1 }) },
            global: { plugins: [PrimeVue] },
        });
        expect(preview.findAll("tbody tr")).toHaveLength(2);
        expect(preview.find("table").attributes("aria-label")).toBe(
            "Rows in the match links file",
        );
        expect(preview.text()).toContain(
            "Some URIs belong to concepts in Lingo.",
        );

        (preview.vm as unknown as { selectedOutcome: string }).selectedOutcome =
            "already_linked";
        await flushPromises();

        expect(preview.findAll("tbody tr")).toHaveLength(1);
        expect(preview.find("tbody").text()).toContain("Jars");
    });

    it("names every outcome, including ones it does not know yet", () => {
        const preview = mount(MatchLinkImportPreview, {
            props: {
                preview: {
                    ...previewWith({}),
                    counts_by_outcome: {
                        conflicting_link: 1,
                        ["future_outcome" as MatchLinkImportOutcome]: 1,
                    },
                },
            },
            global: { plugins: [PrimeVue] },
        });

        expect(preview.text()).toContain(
            "Already linked with another match type: 1",
        );
        expect(preview.text()).toContain("future_outcome: 1");
    });

    it("names the file chooser after its field and help text", () => {
        const upload = mount(MatchLinkImportUpload, {
            props: { isDisabled: false, isSchemeScoped: false },
            global: { plugins: [PrimeVue] },
        });
        const chooseButton = upload.find("button");
        const labelledBy = chooseButton
            .attributes("aria-labelledby")!
            .split(" ");

        expect(labelledBy.map((id) => upload.find(`#${id}`).text())).toEqual([
            "Match links file (CSV)",
            "Choose File",
        ]);
        expect(
            upload
                .find(`#${chooseButton.attributes("aria-describedby")}`)
                .text(),
        ).toContain("Needs concept_id and match_uri columns.");
    });
});
