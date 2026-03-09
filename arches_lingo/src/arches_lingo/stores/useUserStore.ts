import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { fetchUser } from "@/arches_lingo/api.ts";

import type { User } from "@/arches_lingo/types";

export const useUserStore = defineStore("user", () => {
    const user = ref<User | null>(null);

    const isEditor = computed(() => user.value?.is_lingo_editor ?? false);
    const isAnonymous = computed(() => user.value?.is_anonymous ?? true);
    const isAuthenticated = computed(() => !isAnonymous.value);
    const allowAnonymousAccess = computed(
        () => user.value?.allow_anonymous_access ?? false,
    );

    async function initialize() {
        user.value = await fetchUser();
    }

    function setUser(userToSet: User | null) {
        user.value = userToSet;
    }

    return {
        user,
        isEditor,
        isAnonymous,
        isAuthenticated,
        allowAnonymousAccess,
        initialize,
        setUser,
    };
});
