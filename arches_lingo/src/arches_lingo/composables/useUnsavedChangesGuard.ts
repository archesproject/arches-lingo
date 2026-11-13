import { onMounted, onUnmounted } from "vue";

import {
    useConfirmDiscard,
    useEditorDirtyState,
} from "@/arches_lingo/composables/useEditorDirtyState.ts";

import type { Router, RouteLocationNormalized } from "vue-router";

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
    const { isEditorDirty } = useEditorDirtyState();
    const { confirmDiscard } = useConfirmDiscard();

    const removeGuard = router.beforeEach((to, from) => {
        if (!isEditorDirty.value) {
            return true;
        }

        if (isQueryOnlyNavigation(to, from)) {
            return true;
        }

        // Dismissing the confirm (Escape or its close button) cancels the
        // navigation, so the guard always settles.
        return new Promise<boolean>((resolve) => {
            confirmDiscard({
                onDiscard: () => resolve(true),
                onKeepEditing: () => resolve(false),
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

function isQueryOnlyNavigation(
    to: RouteLocationNormalized,
    from: RouteLocationNormalized,
) {
    if (to.path !== from.path) {
        return false;
    }

    return to.fullPath.split("?")[0] === from.fullPath.split("?")[0];
}
