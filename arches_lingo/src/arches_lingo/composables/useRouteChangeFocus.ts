import { nextTick, onUnmounted } from "vue";

import { useAnnouncer } from "@/arches_lingo/composables/useAnnouncer.ts";
import { MAIN_CONTENT_ID } from "@/arches_lingo/constants.ts";
import { focusWithoutScrolling } from "@/arches_lingo/utils.ts";

import type { Ref } from "vue";
import type { Router } from "vue-router";

// Concept and scheme headings render empty until their resource loads.
const PAGE_HEADING_TIMEOUT_MS = 5000;

function findPageHeading(mainContent: HTMLElement) {
    const heading = mainContent.querySelector<HTMLElement>("h1");
    return heading?.textContent?.trim() ? heading : null;
}

function waitForPageHeading(
    mainContent: HTMLElement,
): Promise<HTMLElement | null> {
    const heading = findPageHeading(mainContent);
    if (heading) {
        return Promise.resolve(heading);
    }

    return new Promise((resolve) => {
        const observer = new MutationObserver(() => {
            const loadedHeading = findPageHeading(mainContent);
            if (loadedHeading) {
                finish(loadedHeading);
            }
        });
        const timeoutId = setTimeout(
            () => finish(null),
            PAGE_HEADING_TIMEOUT_MS,
        );

        function finish(result: HTMLElement | null) {
            observer.disconnect();
            clearTimeout(timeoutId);
            resolve(result);
        }

        observer.observe(mainContent, {
            childList: true,
            subtree: true,
            characterData: true,
        });
    });
}

/**
 * After a navigation to a new path (2.4.3, 4.1.3):
 * - when the page type changes, or the old page took the focus with it, focus
 *   moves to the new page's h1 (or to <main> if it has none);
 * - otherwise focus stays where it is (e.g. in the hierarchy tree), and the
 *   label of a newly shown concept or scheme is announced instead.
 *
 * Query-only navigations (filters, paging, the hierarchy toggle) are ignored.
 */
export function useRouteChangeFocus(
    router: Router,
    pageTitleDetail: Ref<string | null>,
) {
    const { announce } = useAnnouncer();
    let latestNavigationId = 0;

    const removeHook = router.afterEach(async (to, from, failure) => {
        const isInitialLoad = from.matched.length === 0;
        if (failure || isInitialLoad || to.path === from.path) {
            return;
        }

        const navigationId = ++latestNavigationId;
        await nextTick();

        const mainContent = document.getElementById(MAIN_CONTENT_ID);
        if (!mainContent) {
            return;
        }

        const focusAfterRender = document.activeElement;
        const heading = await waitForPageHeading(mainContent);

        // Focus can drop to <body> while we wait, e.g. when the mobile nav
        // drawer that held it closes; that isn't the user moving on.
        const hasLostFocus =
            !document.activeElement || document.activeElement === document.body;
        const hasUserMovedFocus =
            document.activeElement !== focusAfterRender && !hasLostFocus;
        if (navigationId !== latestNavigationId || hasUserMovedFocus) {
            return;
        }

        if (to.name !== from.name || hasLostFocus) {
            focusWithoutScrolling(heading ?? mainContent);
        } else if (heading && pageTitleDetail.value) {
            announce(heading.textContent!.trim());
        }
    });

    onUnmounted(removeHook);
}
