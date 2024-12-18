import type { InjectionKey, Ref } from "vue";
import type { Language } from "@/arches_vue_utils/types.ts";
import type { Concept, UserRefAndSetter } from "@/arches_lingo/types.ts";

export const ANONYMOUS = "anonymous";
export const ERROR = "error";
export const SECONDARY = "secondary";
export const CONTRAST = "contrast";
export const EDIT = "edit";
export const VIEW = "view";
export const OPEN_EDITOR = "openEditor";

export const DEFAULT_ERROR_TOAST_LIFE = 8000;
export const SEARCH_RESULTS_PER_PAGE = 25;
export const SEARCH_RESULT_ITEM_SIZE = 38;

// Injection keys
export const USER_KEY = Symbol() as InjectionKey<UserRefAndSetter>;
export const displayedRowKey = Symbol() as InjectionKey<Ref<Concept | null>>;
export const selectedLanguageKey = Symbol() as InjectionKey<Ref<Language>>;
export const systemLanguageKey = Symbol() as InjectionKey<Language>; // not reactive

export const ENGLISH = {
    code: "en",
    default_direction: "ltr" as const,
    id: 1,
    isdefault: true,
    name: "English",
    scope: "system",
};

export const LANGUAGE_CONTROLLED_LIST = "55ce793b-a51a-4b25-811d-d08ea797f8c3";
