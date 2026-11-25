import { ref } from "vue";

import { useConfirm } from "primevue/useconfirm";
import { useGettext } from "vue3-gettext";

import { DANGER, SECONDARY } from "@/arches_lingo/constants.ts";

import type { ConfirmationOptions } from "primevue/confirmationoptions";

// Module-level singleton: tracks whether the currently active editor form has
// unsaved changes.  ComponentEditor writes to this; the router navigation guard
// (see useUnsavedChangesGuard) and non-route UI handlers read from it to decide
// whether to prompt the user before proceeding.
const isEditorDirty = ref(false);
const isUnsavedChangesConfirmOpen = ref(false);

export function useEditorDirtyState() {
    return { isEditorDirty, isUnsavedChangesConfirmOpen };
}

/**
 * Build the common PrimeVue ConfirmationOptions for the "unsaved changes"
 * dialog.  Callers can spread additional keys (e.g. `reject`, `onHide`) on
 * top of the returned object.
 */
export function unsavedChangesConfirmOptions(
    $gettext: (msg: string) => string,
    onAccept: () => void,
): ConfirmationOptions {
    return {
        group: "unsaved-changes",
        header: $gettext("Unsaved Changes"),
        message: $gettext(
            "You have unsaved changes that will be discarded. Do you want to continue?",
        ),
        acceptProps: {
            label: $gettext("Discard Changes"),
            severity: DANGER,
        },
        rejectProps: {
            label: $gettext("Keep Editing"),
            severity: SECONDARY,
            outlined: true,
        },
        accept: onAccept,
    };
}

export interface ConfirmDiscardCallbacks {
    onDiscard: () => void;
    onKeepEditing?: () => void;
}

/**
 * Returns `confirmDiscard`, the one way to open the "Unsaved Changes" confirm.
 *
 * Exactly one callback runs per request: `onDiscard` on "Discard Changes",
 * otherwise `onKeepEditing` ("Keep Editing", the close button or Escape).  If
 * the confirm is already open, the new request keeps editing at once instead
 * of replacing the open confirm.
 *
 * Must be called from a component `setup` context.
 */
export function useConfirmDiscard() {
    const confirm = useConfirm();
    const { $gettext } = useGettext();

    function confirmDiscard({
        onDiscard,
        onKeepEditing,
    }: ConfirmDiscardCallbacks) {
        if (isUnsavedChangesConfirmOpen.value) {
            onKeepEditing?.();
            return;
        }

        isUnsavedChangesConfirmOpen.value = true;
        let isSettled = false;

        function settle(callback?: () => void) {
            if (isSettled) {
                return;
            }
            isSettled = true;
            isUnsavedChangesConfirmOpen.value = false;
            callback?.();
        }

        confirm.require({
            ...unsavedChangesConfirmOptions($gettext, () => settle(onDiscard)),
            reject: () => settle(onKeepEditing),
            onHide: () => settle(onKeepEditing),
        });
    }

    return { confirmDiscard };
}
