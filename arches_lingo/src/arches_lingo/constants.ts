import type { Component, InjectionKey, Ref } from "vue";
import type { Language } from "@/arches_component_lab/types.ts";
import type { Concept } from "@/arches_lingo/types.ts";

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
export const DELETE = "delete";
export const DEPRECATE = "deprecate";
export const STRATEGY_REPARENT = "reparent";
export const STRATEGY_DELETE_CHILDREN = "delete_children";
export const STRATEGY_ORPHAN = "orphan";
export const CONCEPT_TYPE_NODE_ALIAS = "type";

export const DRAFT_LIFECYCLE_STATE_ID = "0e7f8c6d-1f7b-4c2a-9a0c-2b9e0d6c8f11";
export const EDITING_LIFECYCLE_STATE_ID =
    "b3a6a0d2-2b5c-4c2f-9d6c-0c2a5b7d1e8f";
export const RETIRED_LIFECYCLE_STATE_ID =
    "9d2e1c0b-7a6b-4b3d-8c1a-0f2d9e6b0a7c";

export const LABEL_TYPE_LIST_ID = "deb847fc-f4c3-4e82-be19-04641579f129";
export const NOTE_TYPE_LIST_ID = "aba2a0b4-75a4-45ba-8b57-021f3ca92a6a";
export const CONCEPT_TYPE_LIST_ID = "4f9b2c82-59c6-4173-99ea-2a6bfbab6aa2";

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
export const TOP_CONCEPT_ICON = "pi pi-arrow-circle-up";

// Lifecycle state IDs — fixed by migration 0009_update_scheme_concept_lifecycles
export const DRAFT_LIFECYCLE_STATE_ID = "0e7f8c6d-1f7b-4c2a-9a0c-2b9e0d6c8f11";
export const EDITING_LIFECYCLE_STATE_ID =
    "b3a6a0d2-2b5c-4c2f-9d6c-0c2a5b7d1e8f";
export const PUBLISHED_LIFECYCLE_STATE_ID =
    "6b0f1a7b-5b3d-4b2a-8a5b-7c3a1b0f2d9e";
export const RETIRED_LIFECYCLE_STATE_ID =
    "9d2e1c0b-7a6b-4b3d-8c1a-0f2d9e6b0a7c";

// URIs
export const GUIDE_TERM_URI = "http://vocab.getty.edu/page/aat/300386700";

// Injection keys
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
