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
export const UPDATED = "updated";
export const NEW = "new";

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
export const LABEL_CONTROLLED_LIST = "deb847fc-f4c3-4e82-be19-04641579f129";
export const STATUSES_CONTROLLED_LIST = "2cc0e054-ef9b-41ae-8e86-e0c3b4e7ca00";
export const METATYPES_CONTROLLED_LIST = "ef69e772-de53-45fe-98d4-bf3e7b10eb57";
export const EVENT_TYPES_CONTROLLED_LIST =
    "6eaa2c6f-af83-464c-9200-051c4cfe7e8e";
