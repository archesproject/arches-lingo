import { computed, inject, provide, ref } from "vue";

/**
 * String injection key shared with GenericWidget (arches-component-lab).
 * GenericWidget injects this key to self-register and report readiness,
 * so a typed Symbol import is not possible across packages.
 */
export const WIDGET_READY_TRACKER_KEY = "widgetReadyTracker";

export interface WidgetReadyTracker {
    register: () => void;
    reportReady: () => void;
}

/**
 * Call once in an editor component to track when all child GenericWidget
 * instances have finished loading. Returns a computed `allWidgetsReady`
 * that becomes true once every registered widget has reported ready.
 *
 * Widgets self-register via inject — no manual event wiring needed.
 */
export function provideWidgetReadyTracker() {
    const registeredCount = ref(0);
    const readyCount = ref(0);

    const allWidgetsReady = computed(
        () =>
            registeredCount.value > 0 &&
            readyCount.value >= registeredCount.value,
    );

    const tracker: WidgetReadyTracker = {
        register() {
            registeredCount.value++;
        },
        reportReady() {
            readyCount.value++;
        },
    };

    provide(WIDGET_READY_TRACKER_KEY, tracker);

    return { allWidgetsReady };
}

export function useWidgetReadyTracker(): WidgetReadyTracker | undefined {
    return inject<WidgetReadyTracker | undefined>(
        WIDGET_READY_TRACKER_KEY,
        undefined,
    );
}
