import { computed, ref, watch, watchEffect } from "vue";
import { useGettext } from "vue3-gettext";

import type { RouteLocationNormalizedLoaded } from "vue-router";
import type { RouteTitle } from "@/arches_lingo/types.ts";

// Module-level singleton: a page that shows one resource (a concept, a
// scheme) sets its label here once it loads, and the app shell adds it to
// document.title.
const pageTitleDetail = ref<string | null>(null);

export function setPageTitleDetail(detail: string | null | undefined) {
    pageTitleDetail.value = detail || null;
}

export function usePageTitle(route: RouteLocationNormalizedLoaded) {
    const { $gettext } = useGettext();

    const routeTitle = computed(() => {
        const getRouteTitle = route.meta.title as RouteTitle | undefined;
        return getRouteTitle?.($gettext) ?? null;
    });

    const pageTitle = computed(() => {
        if (routeTitle.value && pageTitleDetail.value) {
            return $gettext(
                "%{routeTitle}: %{detail}",
                { routeTitle: routeTitle.value, detail: pageTitleDetail.value },
                true,
            );
        }
        return routeTitle.value;
    });

    const documentTitle = computed(() =>
        [$gettext("Arches Lingo"), pageTitle.value].filter(Boolean).join(" | "),
    );

    // Runs before the new page renders, so it never clears a label that the
    // new page has already set.
    watch(
        () => route.path,
        () => {
            pageTitleDetail.value = null;
        },
    );

    watchEffect(() => {
        document.title = documentTitle.value;
    });

    return { pageTitleDetail };
}
