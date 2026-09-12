import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";

import InlineMarkupText from "@/arches_lingo/components/generic/InlineMarkupText/InlineMarkupText.vue";

function renderMarkup(markup: string) {
    return mount(InlineMarkupText, { props: { markup } });
}

describe("InlineMarkupText", () => {
    it("renders emphasis and links without losing the surrounding spaces", () => {
        const wrapper = renderMarkup(
            "The *AAT* and [GEMET](https://example.org/gemet) are locked.",
        );

        expect(wrapper.text()).toBe("The AAT and GEMET are locked.");
        expect(wrapper.find("em").text()).toBe("AAT");
        expect(wrapper.find("a").attributes("href")).toBe(
            "https://example.org/gemet",
        );
    });

    it("does not introduce whitespace between segments", () => {
        const wrapper = renderMarkup("should **NOT** be treated");

        expect(wrapper.text()).toBe("should NOT be treated");
        expect(/ {2}/.test(wrapper.html())).toBe(false);
    });

    it("keeps punctuation flush against the preceding phrase", () => {
        const wrapper = renderMarkup("**on Sunday**, reverting all edits");

        expect(wrapper.text()).toBe("on Sunday, reverting all edits");
    });

    it("opens external links in a new tab but leaves mailto links in place", () => {
        const external = renderMarkup(
            "[Forum](https://community.example.org/)",
        );
        expect(external.find("a").attributes("target")).toBe("_blank");
        expect(external.find("a").attributes("rel")).toBe(
            "noopener noreferrer",
        );

        const email = renderMarkup("[us](mailto:contact@example.org)");
        expect(email.find("a").attributes("target")).toBeUndefined();
        expect(email.find("a").attributes("rel")).toBeUndefined();
    });
});
