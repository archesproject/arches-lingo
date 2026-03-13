import type { RouteLocationNormalized } from "vue-router";

import {
    resolveSchemeIdentifier,
    resolveConceptIdentifier,
} from "@/arches_lingo/api.ts";

export const routes = [
    {
        path: "/login/:next?",
        name: "login",
        component: () => import("@/arches_lingo/pages/LoginPage.vue"),
        meta: {
            shouldShowNavigation: false,
            requiresAuthentication: false,
        },
    },
    {
        path: "/",
        name: "dashboard",
        component: () => import("@/arches_lingo/pages/HomePage.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/schemes",
        name: "schemes",
        component: () => import("@/arches_lingo/pages/SchemeList.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/advanced-search",
        name: "advanced-search",
        component: () => import("@/arches_lingo/pages/AdvancedSearch.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/concept/:id",
        name: "concept",
        component: () => import("@/arches_lingo/pages/ConceptPage.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/scheme/:id",
        name: "scheme",
        component: () => import("@/arches_lingo/pages/SchemePage.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/schemes/:schemeIdentifier",
        name: "scheme-by-identifier",
        component: () => import("@/arches_lingo/pages/SchemePage.vue"),
        beforeEnter: async (to: RouteLocationNormalized) => {
            const result = await resolveSchemeIdentifier(
                to.params.schemeIdentifier as string,
            );
            if (!result) return false;
            to.meta.resolvedResourceId = result.resourceinstanceid;
        },
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/schemes/:schemeIdentifier/concepts/:conceptIdentifier",
        name: "concept-by-identifier",
        component: () => import("@/arches_lingo/pages/ConceptPage.vue"),
        beforeEnter: async (to: RouteLocationNormalized) => {
            const result = await resolveConceptIdentifier(
                to.params.schemeIdentifier as string,
                to.params.conceptIdentifier as string,
            );
            if (!result) return false;
            to.meta.resolvedResourceId = result.resourceinstanceid;
        },
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/sources",
        name: "sources",
        component: () => import("@/arches_lingo/pages/SourcesPage.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/source/:id",
        name: "source",
        component: () => import("@/arches_lingo/pages/SourcesPage.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/contributors",
        name: "contributors",
        component: () => import("@/arches_lingo/pages/ContributorsPage.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/contributor/:id",
        name: "contributor",
        component: () => import("@/arches_lingo/pages/ContributorsPage.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/profile",
        name: "profile",
        component: () => import("@/arches_lingo/pages/UserProfilePage.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
];

export const routeNames = {
    root: "dashboard",
    login: "login",
    search: "search",
    advancedSearch: "advanced-search",
    dashboard: "dashboard",
    schemes: "schemes",
    concept: "concept",
    scheme: "scheme",
    schemeByIdentifier: "scheme-by-identifier",
    conceptByIdentifier: "concept-by-identifier",
    sources: "sources",
    source: "source",
    contributors: "contributors",
    contributor: "contributor",
    profile: "profile",
};
