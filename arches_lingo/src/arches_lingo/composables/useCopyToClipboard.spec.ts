import { defineComponent, h } from "vue";

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useCopyToClipboard } from "@/arches_lingo/composables/useCopyToClipboard.ts";

const toastAdd = vi.fn();

vi.mock("primevue/usetoast", () => ({
    useToast: () => ({ add: toastAdd }),
}));

vi.mock("vue3-gettext", () => ({
    useGettext: () => ({ $gettext: (text: string) => text }),
}));

const TOAST_SUMMARIES = {
    copiedSummary: "Copied",
    failedSummary: "Not copied",
};

function setClipboard(clipboard: Partial<Clipboard> | undefined): void {
    Object.defineProperty(navigator, "clipboard", {
        value: clipboard,
        configurable: true,
    });
}

function mountComposable(): ReturnType<typeof useCopyToClipboard> {
    let exposed!: ReturnType<typeof useCopyToClipboard>;
    mount(
        defineComponent({
            setup() {
                exposed = useCopyToClipboard();
                return () => h("div");
            },
        }),
    );
    return exposed;
}

describe("useCopyToClipboard", () => {
    beforeEach(() => {
        toastAdd.mockReset();
    });

    afterEach(() => {
        setClipboard(undefined);
    });

    it("copies the text and confirms with a success toast", async () => {
        const writeText = vi.fn().mockResolvedValue(undefined);
        setClipboard({ writeText });

        await mountComposable().copyToClipboard("copied text", TOAST_SUMMARIES);

        expect(writeText).toHaveBeenCalledWith("copied text");
        expect(toastAdd).toHaveBeenCalledWith(
            expect.objectContaining({ severity: "success", summary: "Copied" }),
        );
    });

    it("reports a refused copy without exposing the browser's error", async () => {
        setClipboard({
            writeText: vi.fn().mockRejectedValue(new Error("denied")),
        });

        await mountComposable().copyToClipboard("copied text", TOAST_SUMMARIES);

        expect(toastAdd).toHaveBeenCalledWith(
            expect.objectContaining({
                severity: "error",
                summary: "Not copied",
                detail: "Select the text and copy it manually.",
            }),
        );
    });

    it("reports a failed copy where the clipboard API is unavailable", async () => {
        setClipboard(undefined);

        await mountComposable().copyToClipboard("copied text", TOAST_SUMMARIES);

        expect(toastAdd).toHaveBeenCalledWith(
            expect.objectContaining({
                severity: "error",
                summary: "Not copied",
            }),
        );
    });
});
