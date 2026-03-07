import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { fetchLingoUser } from "@/arches_lingo/api.ts";

import type { LingoUser } from "@/arches_lingo/types";

export const useLingoUserStore = defineStore("lingoUser", () => {
    const lingoUser = ref<LingoUser | null>(null);

    const isEditor = computed(() => lingoUser.value?.is_editor ?? false);
    const isAnonymous = computed(() => lingoUser.value?.is_anonymous ?? true);
    const isAuthenticated = computed(() => !isAnonymous.value);
    const allowAnonymousAccess = computed(
        () => lingoUser.value?.allow_anonymous_access ?? false,
    );

    async function initialize() {
        lingoUser.value = await fetchLingoUser();
    }

    return {
        lingoUser,
        isEditor,
        isAnonymous,
        isAuthenticated,
        allowAnonymousAccess,
        initialize,
    };
});
