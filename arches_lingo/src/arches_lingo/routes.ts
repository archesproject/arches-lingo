export const routes = [
    // {
    //     path: "/",
    //     name: "root",
    //     component: () => import("@/arches_lingo/pages/HomePage.vue"),
    //     meta: {
    //         shouldShowNavigation: true,
    //         requiresAuthentication: true,
    //     },
    // },
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
        path: "/",
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
        component: () => import("@/arches_lingo/pages/ConceptPage.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: "/scheme/:id",
        name: "scheme",
        component: () => import("@/arches_lingo/pages/SchemePage.vue"),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
];

export const routeNames = {
    root: "schemes",
    login: "login",
    search: "search",
    advancedSearch: "advanced-search",
    schemes: "schemes",
    concept: "concept",
    scheme: "scheme",
};
