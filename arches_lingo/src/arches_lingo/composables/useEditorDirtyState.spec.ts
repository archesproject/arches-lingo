import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ConfirmationOptions } from "primevue/confirmationoptions";

const requiredConfirmations: ConfirmationOptions[] = [];

vi.mock("primevue/useconfirm", () => ({
    useConfirm: () => ({
        require: (options: ConfirmationOptions) =>
            requiredConfirmations.push(options),
    }),
}));

vi.mock("vue3-gettext", () => ({
    useGettext: () => ({ $gettext: (message: string) => message }),
}));

import {
    useConfirmDiscard,
    useEditorDirtyState,
} from "@/arches_lingo/composables/useEditorDirtyState.ts";

describe("useConfirmDiscard", () => {
    const { isUnsavedChangesConfirmOpen } = useEditorDirtyState();

    beforeEach(() => {
        requiredConfirmations.length = 0;
    });

    afterEach(() => {
        isUnsavedChangesConfirmOpen.value = false;
    });

    it("runs onDiscard once and clears the open flag on accept", () => {
        const onDiscard = vi.fn();
        const onKeepEditing = vi.fn();
        const { confirmDiscard } = useConfirmDiscard();

        confirmDiscard({ onDiscard, onKeepEditing });
        expect(isUnsavedChangesConfirmOpen.value).toBe(true);

        requiredConfirmations[0].accept!();
        requiredConfirmations[0].onHide!();

        expect(onDiscard).toHaveBeenCalledTimes(1);
        expect(onKeepEditing).toHaveBeenCalledTimes(0);
        expect(isUnsavedChangesConfirmOpen.value).toBe(false);
    });

    it("keeps editing when the confirm is dismissed", () => {
        const onDiscard = vi.fn();
        const onKeepEditing = vi.fn();
        const { confirmDiscard } = useConfirmDiscard();

        confirmDiscard({ onDiscard, onKeepEditing });
        requiredConfirmations[0].onHide!();

        expect(onKeepEditing).toHaveBeenCalledTimes(1);
        expect(onDiscard).toHaveBeenCalledTimes(0);
        expect(isUnsavedChangesConfirmOpen.value).toBe(false);
    });

    it("does not replace a confirm that is already open", () => {
        const firstOnDiscard = vi.fn();
        const secondOnKeepEditing = vi.fn();
        const { confirmDiscard } = useConfirmDiscard();

        confirmDiscard({ onDiscard: firstOnDiscard });
        confirmDiscard({
            onDiscard: vi.fn(),
            onKeepEditing: secondOnKeepEditing,
        });

        expect(requiredConfirmations).toHaveLength(1);
        expect(secondOnKeepEditing).toHaveBeenCalledTimes(1);

        requiredConfirmations[0].accept!();
        expect(firstOnDiscard).toHaveBeenCalledTimes(1);
    });
});
