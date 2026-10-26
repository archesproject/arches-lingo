import { defineComponent, h } from "vue";

import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter, useRoute } from "vue-router";
import { describe, expect, it, vi } from "vitest";

import {
    setPageTitleDetail,
    usePageTitle,
} from "@/arches_lingo/composables/usePageTitle.ts";

import type { TranslateFunction } from "@/arches_lingo/types.ts";

vi.mock("vue3-gettext", () => ({
    useGettext: () => ({
        $gettext: (text: string, params: Record<string, string> = {}) =>
            text.replace(/%\{(\w+)\}/g, (_match, key) => params[key]),
    }),
}));

async function mountShellAt(path: string) {
    const router = createRouter({
        history: createMemoryHistory(),
        routes: [
            {
                path: "/",
                name: "landing",
                component: { render: () => null },
            },
            {
                path: "/concept/:id",
                name: "concept",
                component: { render: () => null },
                meta: {
                    title: ($gettext: TranslateFunction) => $gettext("Concept"),
                },
            },
        ],
    });
    await router.push(path);
    await router.isReady();

    mount(
        defineComponent({
            setup() {
                usePageTitle(useRoute());
                return () => h("div");
            },
        }),
        { global: { plugins: [router] } },
    );
    await flushPromises();
    return router;
}

describe("usePageTitle", () => {
    it("uses the app name alone when the route has no title", async () => {
        await mountShellAt("/");

        expect(document.title).toBe("Arches Lingo");
    });

    it("adds the loaded resource label after the route title", async () => {
        await mountShellAt("/concept/1");
        expect(document.title).toBe("Arches Lingo | Concept");

        setPageTitleDetail("Birds");
        await flushPromises();
        expect(document.title).toBe("Arches Lingo | Concept: Birds");
    });

    it("drops the label when the path changes", async () => {
        const router = await mountShellAt("/concept/1");
        setPageTitleDetail("Birds");
        await flushPromises();

        await router.push("/concept/2");
        await flushPromises();
        expect(document.title).toBe("Arches Lingo | Concept");
    });
});
