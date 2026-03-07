import type { Component, InjectionKey, Ref } from "vue";
import type { Language } from "@/arches_component_lab/types.ts";
import type { Concept, UserRefAndSetter } from "@/arches_lingo/types.ts";

export const ANONYMOUS = "anonymous";
export const ERROR = "error";
export const SUCCESS = "success";
export const DANGER = "danger";
export const SECONDARY = "secondary";
export const CONTRAST = "contrast";
export const EDIT = "edit";
export const VIEW = "view";
export const OPEN_EDITOR = "openEditor";
export const UPDATED = "updated";
export const NEW = "new";
export const MAXIMIZE = "maximize";
export const MAXIMIZED = "maximized";
export const MINIMIZE = "minimize";
export const MINIMIZED = "minimized";
export const CLOSE = "close";
export const CLOSED = "closed";
export const NEW_CONCEPT = "newConcept";
export const CONCEPT_TYPE_NODE_ALIAS = "type";

export const DEFAULT_TOAST_LIFE = 5000;
export const DEFAULT_ERROR_TOAST_LIFE = 8000;
export const SEARCH_RESULTS_PER_PAGE = 25;
export const SEARCH_RESULT_ITEM_SIZE = 50;

export const FALLBACK_LANGUAGE: Language = {
    code: "en",
    default_direction: "ltr",
    id: 0,
    isdefault: true,
    name: "English",
    scope: "system",
};

// Icons
export const CONCEPT_ICON = "pi pi-tag";
export const GUIDE_TERM_ICON = "pi pi-angle-double-right";
export const SCHEME_ICON = "pi pi-folder";

// URIs
export const GUIDE_TERM_URI = "http://vocab.getty.edu/page/aat/300386700";

// Injection keys
export const USER_KEY = Symbol() as InjectionKey<UserRefAndSetter>;
export const openPanelComponentKey = Symbol() as InjectionKey<
    (
        component: Component,
        componentName: string,
        sectionTitle: string,
        graphSlug?: string,
        nodegroupAlias?: string,
    ) => void
>;
export const displayedRowKey = Symbol() as InjectionKey<Ref<Concept | null>>;
