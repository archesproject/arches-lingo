import { onMounted, onUnmounted } from "vue";

import { useGettext } from "vue3-gettext";
import { useConfirm } from "primevue/useconfirm";

import {
    useEditorDirtyState,
    unsavedChangesConfirmOptions,
} from "@/arches_lingo/composables/useEditorDirtyState.ts";

import type { Router } from "vue-router";

/**
 * Composable that installs:
 *
 * 1. A global `router.beforeEach` guard that prompts the user with a PrimeVue
 *    ConfirmDialog whenever a route change is attempted while the editor form
 *    has unsaved changes.
 * 2. A `beforeunload` listener that triggers the browser's native "Leave
 *    site?" dialog on refresh / tab close when there are unsaved changes.
 *
 * Must be called from a component `setup` context (it relies on `useConfirm`,
 * `useGettext`, and Vue lifecycle hooks).
 */
export function useUnsavedChangesGuard(router: Router) {
    const { $gettext } = useGettext();
    const confirm = useConfirm();
    const { isEditorDirty } = useEditorDirtyState();

    const removeGuard = router.beforeEach(() => {
        if (!isEditorDirty.value) {
            return true;
        }

        return new Promise<boolean>((resolve) => {
            confirm.require({
                ...unsavedChangesConfirmOptions($gettext, () => resolve(true)),
                reject: () => resolve(false),
            });
        });
    });

    function onBeforeUnload(event: BeforeUnloadEvent) {
        if (isEditorDirty.value) {
            event.preventDefault();
        }
    }

    onMounted(() => window.addEventListener("beforeunload", onBeforeUnload));
    onUnmounted(() => {
        window.removeEventListener("beforeunload", onBeforeUnload);
        removeGuard();
    });
}
