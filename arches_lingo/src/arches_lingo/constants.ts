import type { InjectionKey } from "vue";

import type { UserRefAndSetter } from "@/arches_lingo/types.ts";

export const ANONYMOUS = "anonymous";
export const ERROR = "error";
export const SECONDARY = "secondary";
export const DEFAULT_ERROR_TOAST_LIFE = 8000;

export const USER_KEY = Symbol() as InjectionKey<UserRefAndSetter>;
