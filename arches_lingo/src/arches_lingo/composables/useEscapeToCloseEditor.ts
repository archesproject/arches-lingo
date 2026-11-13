import { onMounted, onUnmounted } from "vue";

import {
    useConfirmDiscard,
    useEditorDirtyState,
} from "@/arches_lingo/composables/useEditorDirtyState.ts";

// Overlays that should handle an Escape keypress before the editor does.
const ESCAPE_OWNER_SELECTOR = [
    ".p-dialog",
    ".p-drawer",
    ".p-popover",
    "[data-pc-section='overlay']",
    "[role='combobox'][aria-expanded='true']",
    "[aria-haspopup][aria-expanded='true']",
].join(", ");

function isEscapeOwnedByOverlay(event: KeyboardEvent) {
    const target = event.target;
    return (
        target instanceof Element &&
        target.closest(ESCAPE_OWNER_SELECTOR) !== null
    );
}

export interface EscapeToCloseEditorOptions {
    isEditorOpen: () => boolean;
    closeEditor: () => void;
}

/**
 * Lets Escape close the open editor from anywhere on the page, asking first
 * when it has unsaved changes.  Escape that belongs to an open dialog, drawer,
 * popover or dropdown is left alone.
 *
 * Must be called from a component `setup` context.
 */
export function useEscapeToCloseEditor({
    isEditorOpen,
    closeEditor,
}: EscapeToCloseEditorOptions) {
    const { isEditorDirty, isUnsavedChangesConfirmOpen } =
        useEditorDirtyState();
    const { confirmDiscard } = useConfirmDiscard();

    function onWindowKeydown(event: KeyboardEvent) {
        if (event.key !== "Escape" || !isEditorOpen()) {
            return;
        }
        if (
            event.defaultPrevented ||
            isUnsavedChangesConfirmOpen.value ||
            isEscapeOwnedByOverlay(event)
        ) {
            return;
        }
        if (isEditorDirty.value) {
            // Stop propagation so PrimeVue's document-level keydown handler
            // doesn't immediately close the dialog we're about to open.
            event.stopPropagation();
            confirmDiscard({ onDiscard: closeEditor });
        } else {
            closeEditor();
        }
    }

    onMounted(() => window.addEventListener("keydown", onWindowKeydown, true));
    onUnmounted(() =>
        window.removeEventListener("keydown", onWindowKeydown, true),
    );
}
