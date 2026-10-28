import { defineComponent, h } from "vue";

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useMediaQuery } from "@/arches_lingo/composables/useMediaQuery.ts";

import type { Ref } from "vue";

function stubMatchMedia(initialMatches: boolean) {
    const listeners = new Set<(event: MediaQueryListEvent) => void>();
    const mediaQueryList = {
        matches: initialMatches,
        addEventListener: vi.fn(
            (_type: string, listener: (event: MediaQueryListEvent) => void) =>
                listeners.add(listener),
        ),
        removeEventListener: vi.fn(
            (_type: string, listener: (event: MediaQueryListEvent) => void) =>
                listeners.delete(listener),
        ),
    };
    vi.stubGlobal(
        "matchMedia",
        vi.fn(() => mediaQueryList),
    );

    function setMatches(matches: boolean) {
        listeners.forEach((listener) =>
            listener({ matches } as MediaQueryListEvent),
        );
    }

    return { listeners, setMatches };
}

function mountWithMediaQuery(query: string) {
    let matches: Ref<boolean> | undefined;
    const wrapper = mount(
        defineComponent({
            setup() {
                matches = useMediaQuery(query);
                return () => h("div");
            },
        }),
    );
    return { wrapper, matches: matches! };
}

describe("useMediaQuery", () => {
    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it("follows the media query as it changes", () => {
        const { setMatches } = stubMatchMedia(false);
        const { matches } = mountWithMediaQuery("(max-width: 960px)");

        expect(matches.value).toBe(false);
        setMatches(true);
        expect(matches.value).toBe(true);
    });

    it("stops listening when the component unmounts", () => {
        const { listeners } = stubMatchMedia(true);
        const { wrapper, matches } = mountWithMediaQuery("(max-width: 960px)");

        expect(matches.value).toBe(true);
        wrapper.unmount();
        expect(listeners.size).toBe(0);
    });
});
