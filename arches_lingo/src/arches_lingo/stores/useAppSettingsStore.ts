import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { fetchAppSettings } from "@/arches_lingo/api.ts";

import type { AppSettings } from "@/arches_lingo/types";

export const useAppSettingsStore = defineStore("appSettings", () => {
    const settings = ref<AppSettings | null>(null);

    const allowAnonymousAccess = computed(
        () => settings.value?.allow_anonymous_access ?? false,
    );

    const publicServerAddress = computed(
        () => settings.value?.public_server_address ?? undefined,
    );

    async function initialize() {
        settings.value = await fetchAppSettings();
    }

    return {
        settings,
        allowAnonymousAccess,
        publicServerAddress,
        initialize,
    };
});
