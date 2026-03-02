import { ref } from "vue";

import { DANGER, SECONDARY } from "@/arches_lingo/constants.ts";

import type { ConfirmationOptions } from "primevue/confirmationoptions";

// Module-level singleton: tracks whether the currently active editor form has
// unsaved changes.  ComponentEditor writes to this; the router navigation guard
// (see useUnsavedChangesGuard) and non-route UI handlers read from it to decide
// whether to prompt the user before proceeding.
const isEditorDirty = ref(false);

export function useEditorDirtyState() {
    return { isEditorDirty };
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
