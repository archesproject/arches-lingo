import { ref } from "vue";

import { focusWithoutScrolling } from "@/arches_lingo/utils.ts";

// PrimeVue Dialog restores focus only when its leave transition runs, which a
// v-if unmount skips, so the dialog stays mounted until `after-hide`.
export function useDialogFocusReturn(
    getFallbackFocusTarget?: () => HTMLElement | null | undefined,
) {
    const isDialogMounted = ref(false);
    const isDialogVisible = ref(false);
    let triggerElement: HTMLElement | null = null;
    let shouldFocusFallbackAfterHide = false;

    function openDialog() {
        triggerElement =
            document.activeElement instanceof HTMLElement
                ? document.activeElement
                : null;
        shouldFocusFallbackAfterHide = false;
        isDialogMounted.value = true;
        isDialogVisible.value = true;
    }

    function closeDialog({ shouldFocusFallback = false } = {}) {
        shouldFocusFallbackAfterHide = shouldFocusFallback;
        isDialogVisible.value = false;
    }

    function onDialogAfterHide() {
        isDialogMounted.value = false;

        if (!shouldFocusFallbackAfterHide && triggerElement?.isConnected) {
            triggerElement.focus();
        } else {
            const fallbackFocusTarget = getFallbackFocusTarget?.();
            if (fallbackFocusTarget) {
                focusWithoutScrolling(fallbackFocusTarget);
            }
        }
        triggerElement = null;
    }

    return {
        isDialogMounted,
        isDialogVisible,
        openDialog,
        closeDialog,
        onDialogAfterHide,
    };
}
