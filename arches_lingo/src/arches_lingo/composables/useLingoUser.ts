import { computed, inject } from "vue";
import { LINGO_USER_KEY } from "@/arches_lingo/constants.ts";

import type { LingoUserRefAndSetter } from "@/arches_lingo/types.ts";

export function useLingoUser() {
    const { lingoUser } = inject(LINGO_USER_KEY) as LingoUserRefAndSetter;

    const isEditor = computed(() => lingoUser.value?.is_editor ?? false);
    const isAnonymous = computed(() => lingoUser.value?.is_anonymous ?? true);
    const isAuthenticated = computed(() => !isAnonymous.value);

    return { lingoUser, isEditor, isAnonymous, isAuthenticated };
}
