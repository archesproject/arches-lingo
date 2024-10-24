export const routes = [
    {
        path: "/",
        name: "root",
        component: () => import("@/arches_lingo/pages/HomePage.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
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
        path: "/advanced-search",
        name: "advanced-search",
        component: () => import("@/arches_lingo/pages/AdvancedSearch.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: "/schemes",
        name: "schemes",
        component: () => import("@/arches_lingo/pages/SchemeList.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: "/concept/:id",
        name: "concept",
        component: () => import("@/arches_lingo/pages/ConceptOrSchemeBase.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: "/scheme/:id",
        name: "scheme",
        component: () => import("@/arches_lingo/pages/ConceptOrSchemeBase.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
];

export const routeNames = {
    root: "root",
    login: "login",
    search: "search",
    advancedSearch: "advanced-search",
    schemes: "schemes",
    concept: "concept",
    scheme: "scheme",
};
