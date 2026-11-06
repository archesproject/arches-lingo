import type { RouteLocationNormalized } from "vue-router";
import type { TranslateFunction } from "@/arches_lingo/types.ts";

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
            title: ($gettext: TranslateFunction) => $gettext("Login"),
            shouldShowNavigation: false,
            requiresAuthentication: false,
            alwaysPublic: true,
        },
    },
    {
        path: "/",
        name: "landing",
        component: () => import("@/arches_lingo/pages/LandingPage.vue"),
        meta: {
            shouldShowNavigation: false,
            requiresAuthentication: false,
            alwaysPublic: true,
        },
    },
    {
        path: "/dashboard",
        name: "dashboard",
        component: () => import("@/arches_lingo/pages/HomePage.vue"),
        meta: {
            title: ($gettext: TranslateFunction) => $gettext("Dashboard"),
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/schemes",
        name: "schemes",
        component: () => import("@/arches_lingo/pages/SchemeList.vue"),
        meta: {
            title: ($gettext: TranslateFunction) => $gettext("Schemes"),
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/advanced-search",
        name: "advanced-search",
        component: () => import("@/arches_lingo/pages/AdvancedSearch.vue"),
        meta: {
            title: ($gettext: TranslateFunction) => $gettext("Advanced Search"),
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/concept-matches/:runId?",
        name: "concept-matches",
        component: () => import("@/arches_lingo/pages/ConceptMatchesPage.vue"),
        meta: {
            title: ($gettext: TranslateFunction) => $gettext("Find Matches"),
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: "/concept/:id",
        name: "concept",
        component: () => import("@/arches_lingo/pages/ConceptPage.vue"),
        meta: {
            title: ($gettext: TranslateFunction) => $gettext("Concept"),
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/scheme/:id",
        name: "scheme",
        component: () => import("@/arches_lingo/pages/SchemePage.vue"),
        meta: {
            title: ($gettext: TranslateFunction) => $gettext("Scheme"),
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
            title: ($gettext: TranslateFunction) => $gettext("Scheme"),
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
            title: ($gettext: TranslateFunction) => $gettext("Concept"),
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/sources",
        name: "sources",
        component: () => import("@/arches_lingo/pages/SourcesPage.vue"),
        meta: {
            title: ($gettext: TranslateFunction) => $gettext("Sources"),
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/source/:id",
        name: "source",
        component: () => import("@/arches_lingo/pages/SourcesPage.vue"),
        meta: {
            title: ($gettext: TranslateFunction) => $gettext("Sources"),
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/contributors",
        name: "contributors",
        component: () => import("@/arches_lingo/pages/ContributorsPage.vue"),
        meta: {
            title: ($gettext: TranslateFunction) => $gettext("Contributors"),
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/contributor/:id",
        name: "contributor",
        component: () => import("@/arches_lingo/pages/ContributorsPage.vue"),
        meta: {
            title: ($gettext: TranslateFunction) => $gettext("Contributors"),
            shouldShowNavigation: true,
            requiresAuthentication: false,
        },
    },
    {
        path: "/profile",
        name: "profile",
        component: () => import("@/arches_lingo/pages/UserProfilePage.vue"),
        meta: {
            title: ($gettext: TranslateFunction) => $gettext("My Profile"),
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
];

export const routeNames = {
    root: "landing",
    login: "login",
    landing: "landing",
    search: "search",
    advancedSearch: "advanced-search",
    conceptMatches: "concept-matches",
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
