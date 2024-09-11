import type { InjectionKey, Ref } from "vue";
import type { Language } from "@/arches_vue_utils/types";
import type {
    Concept,
    HeaderRefAndSetter,
    UserRefAndSetter,
} from "@/arches_lingo/types.ts";

export const ANONYMOUS = "anonymous";
export const ERROR = "error";
export const SECONDARY = "secondary";
export const CONTRAST = "contrast";
export const DEFAULT_ERROR_TOAST_LIFE = 8000;

// Injection keys
export const USER_KEY = Symbol() as InjectionKey<UserRefAndSetter>;
export const displayedRowKey = Symbol() as InjectionKey<Ref<Concept | null>>;
export const headerKey = Symbol() as InjectionKey<HeaderRefAndSetter>;
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
