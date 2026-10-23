import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { fetchAppSettings } from "@/arches_lingo/api.ts";

import type { AppSettings } from "@/arches_lingo/types";

export const useAppSettingsStore = defineStore("appSettings", () => {
    const settings = ref<AppSettings | null>(null);

    const allowAnonymousAccess = computed(
        () => settings.value?.allow_anonymous_access ?? false,
    );

    const reconciliationEnabled = computed(
        () => settings.value?.reconciliation_enabled ?? false,
    );

    const reconciliationServiceUrl = computed(
        () => settings.value?.reconciliation_service_url ?? null,
    );

    const schemeReconciliationServiceUrlTemplate = computed(
        () =>
            settings.value?.scheme_reconciliation_service_url_template ?? null,
    );

    const publicServerAddress = computed(
        () => settings.value?.public_server_address ?? undefined,
    );

    const archesVersion = computed(() => settings.value?.arches_version ?? "");

    const lingoVersion = computed(() => settings.value?.lingo_version ?? "");

    async function initialize() {
        if (settings.value !== null) return;
        settings.value = await fetchAppSettings();
    }

    return {
        settings,
        allowAnonymousAccess,
        reconciliationEnabled,
        reconciliationServiceUrl,
        schemeReconciliationServiceUrlTemplate,
        publicServerAddress,
        archesVersion,
        lingoVersion,
        initialize,
    };
});
