import { nextTick, onBeforeUnmount, onMounted } from "vue";
import { storeToRefs } from "pinia";

import ToastEventBus from "primevue/toasteventbus";

import { ERROR } from "@/arches_lingo/constants.ts";
import { useAppSettingsStore } from "@/arches_lingo/stores/useAppSettingsStore.ts";

import type {
    ToastMessageOptions,
    ToastPassThroughMethodOptions,
} from "primevue/toast";

const TOAST_MESSAGE_SELECTOR = ".p-toast-message";
const OPEN_TOAST_CLOSE_BUTTON_SELECTOR =
    ".p-toast-message:not(.p-toast-message-leave-active) .p-toast-close-button";
const TOAST_ID_ATTRIBUTE = "data-toast-id";

type ToastMessageWithId = ToastMessageOptions & { id?: number };

export const TOAST_MESSAGE_PASS_THROUGH = ({
    instance,
}: ToastPassThroughMethodOptions) => ({
    [TOAST_ID_ATTRIBUTE]: instance.message?.id,
});

// In ACCESSIBILITY_MODE, errors and toasts with a detail stay open and take focus (2.2.1).
export function useAccessibleToasts() {
    const { isAccessibilityMode } = storeToRefs(useAppSettingsStore());
    let focusBeforeToasts: HTMLElement | null = null;

    function isInsideToast(element: Element | null) {
        return Boolean(element?.closest(TOAST_MESSAGE_SELECTOR));
    }

    function focusNewestToast() {
        const closeButtons = document.querySelectorAll<HTMLElement>(
            OPEN_TOAST_CLOSE_BUTTON_SELECTOR,
        );
        closeButtons[closeButtons.length - 1]?.focus();
        return closeButtons.length > 0;
    }

    function focusToast(toastId: ToastMessageWithId["id"]) {
        document
            .querySelector<HTMLElement>(
                `[${TOAST_ID_ATTRIBUTE}="${String(toastId)}"] .p-toast-close-button`,
            )
            ?.focus();
    }

    async function makeToastSticky(message: ToastMessageWithId) {
        const isStickyToast = message.severity === ERROR || message.detail;
        if (!isAccessibilityMode.value || !isStickyToast) {
            return;
        }
        message.life = 0;

        if (!isInsideToast(document.activeElement)) {
            focusBeforeToasts =
                document.activeElement instanceof HTMLElement
                    ? document.activeElement
                    : null;
        }
        await nextTick();
        focusToast(message.id);
    }

    function onToastKeydown(event: KeyboardEvent) {
        if (event.key !== "Escape" || !(event.target instanceof Element)) {
            return;
        }
        event.target
            .closest(TOAST_MESSAGE_SELECTOR)
            ?.querySelector<HTMLElement>(".p-toast-close-button")
            ?.click();
    }

    async function onToastClose() {
        const activeElement = document.activeElement;
        if (activeElement !== document.body && !isInsideToast(activeElement)) {
            return;
        }
        await nextTick();
        if (focusNewestToast()) {
            return;
        }
        if (focusBeforeToasts?.isConnected) {
            focusBeforeToasts.focus();
        }
        focusBeforeToasts = null;
    }

    onMounted(() => ToastEventBus.on("add", makeToastSticky));
    onBeforeUnmount(() => ToastEventBus.off("add", makeToastSticky));

    return { onToastKeydown, onToastClose };
}
