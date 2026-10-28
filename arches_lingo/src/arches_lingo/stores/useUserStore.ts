import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { fetchUser } from "@/arches_lingo/api.ts";

import type { User } from "@/arches_lingo/types";

export const useUserStore = defineStore("user", () => {
    const user = ref<User | null>(null);

    const isEditor = computed(() => user.value?.is_lingo_editor ?? false);
    const isLingoAdmin = computed(() => user.value?.is_lingo_admin ?? false);
    const isAnonymous = computed(() => user.value?.is_anonymous ?? true);
    const isStaff = computed(() => user.value?.is_staff ?? false);
    const canExport = computed(() => user.value?.is_lingo_exporter ?? false);

    async function refresh() {
        user.value = await fetchUser();
    }

    function setUser(userToSet: User | null) {
        user.value = userToSet;
    }

    return {
        user,
        isEditor,
        isLingoAdmin,
        isAnonymous,
        isStaff,
        canExport,
        refresh,
        setUser,
    };
});
