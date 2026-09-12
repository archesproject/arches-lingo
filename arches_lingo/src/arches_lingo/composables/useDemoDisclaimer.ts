import { computed, ref } from "vue";

import { useAppSettingsStore } from "@/arches_lingo/stores/useAppSettingsStore.ts";
import { DEMO_DISCLAIMER_ACKNOWLEDGED_LOCAL_STORAGE_KEY } from "@/arches_lingo/constants.ts";

// Module-level singleton: the disclaimer dialog and the header button that
// reopens it sit in different branches of the component tree, so they share
// acknowledgement state here rather than passing it through PageHeader.
const hasAcknowledgedDemoDisclaimer = ref(
    localStorage.getItem(DEMO_DISCLAIMER_ACKNOWLEDGED_LOCAL_STORAGE_KEY) ===
        "true",
);

// Set when the user reopens the disclaimer from the header, which shows the
// dialog again without discarding the stored acknowledgement.
const wasDemoDisclaimerReopened = ref(false);

export function useDemoDisclaimer() {
    const appSettingsStore = useAppSettingsStore();

    const isDemoDisclaimerEnabled = computed(
        () => appSettingsStore.showDemoDisclaimer,
    );

    const isDemoDisclaimerVisible = computed(
        () =>
            isDemoDisclaimerEnabled.value &&
            (wasDemoDisclaimerReopened.value ||
                !hasAcknowledgedDemoDisclaimer.value),
    );

    function acknowledgeDemoDisclaimer() {
        localStorage.setItem(
            DEMO_DISCLAIMER_ACKNOWLEDGED_LOCAL_STORAGE_KEY,
            "true",
        );
        hasAcknowledgedDemoDisclaimer.value = true;
        wasDemoDisclaimerReopened.value = false;
    }

    function openDemoDisclaimer() {
        wasDemoDisclaimerReopened.value = true;
    }

    return {
        isDemoDisclaimerEnabled,
        isDemoDisclaimerVisible,
        acknowledgeDemoDisclaimer,
        openDemoDisclaimer,
    };
}
