import { afterEach, describe, expect, it } from "vitest";

import { useDialogFocusReturn } from "@/arches_lingo/composables/useDialogFocusReturn.ts";

function addButton(text: string) {
    const button = document.createElement("button");
    button.textContent = text;
    document.body.append(button);
    return button;
}

describe("useDialogFocusReturn", () => {
    afterEach(() => {
        document.body.replaceChildren();
    });

    it("stays mounted until the dialog has hidden", () => {
        const { isDialogMounted, isDialogVisible, openDialog, closeDialog } =
            useDialogFocusReturn();

        openDialog();
        closeDialog();

        expect(isDialogVisible.value).toBe(false);
        expect(isDialogMounted.value).toBe(true);
    });

    it("returns focus to the trigger after hiding", () => {
        const trigger = addButton("Delete");
        const elsewhere = addButton("Elsewhere");
        const { isDialogMounted, openDialog, closeDialog, onDialogAfterHide } =
            useDialogFocusReturn();

        trigger.focus();
        openDialog();
        elsewhere.focus();
        closeDialog();
        onDialogAfterHide();

        expect(isDialogMounted.value).toBe(false);
        expect(document.activeElement).toBe(trigger);
    });

    it("focuses the fallback when the trigger is gone", () => {
        const trigger = addButton("Retire");
        const heading = document.createElement("h1");
        document.body.append(heading);
        const { openDialog, onDialogAfterHide } = useDialogFocusReturn(
            () => heading,
        );

        trigger.focus();
        openDialog();
        trigger.remove();
        onDialogAfterHide();

        expect(document.activeElement).toBe(heading);
        expect(heading.getAttribute("tabindex")).toBe("-1");
    });

    it("focuses the fallback when asked to, even if the trigger remains", () => {
        const trigger = addButton("Merge");
        const statusRegion = document.createElement("div");
        document.body.append(statusRegion);
        const { openDialog, closeDialog, onDialogAfterHide } =
            useDialogFocusReturn(() => statusRegion);

        trigger.focus();
        openDialog();
        closeDialog({ shouldFocusFallback: true });
        onDialogAfterHide();

        expect(document.activeElement).toBe(statusRegion);
    });
});
