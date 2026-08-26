import { describe, expect, it } from "vitest";

import { parseInlineMarkup } from "@/arches_lingo/components/generic/InlineMarkupText/parseInlineMarkup.ts";

describe("parseInlineMarkup", () => {
    it("returns a single plain segment when there is no markup", () => {
        expect(parseInlineMarkup("For official vocabularies, see:")).toEqual([
            { text: "For official vocabularies, see:" },
        ]);
    });

    it("preserves the spacing surrounding each marked-up phrase", () => {
        expect(parseInlineMarkup("The *AAT* and *GEMET* are locked.")).toEqual([
            { text: "The " },
            { text: "AAT", style: "emphasis" },
            { text: " and " },
            { text: "GEMET", style: "emphasis" },
            { text: " are locked." },
        ]);
    });

    it("does not treat a strong run as two emphasis markers", () => {
        expect(parseInlineMarkup("should **NOT** be treated")).toEqual([
            { text: "should " },
            { text: "NOT", style: "strong" },
            { text: " be treated" },
        ]);
    });

    it("keeps punctuation that directly follows a marked-up phrase", () => {
        expect(
            parseInlineMarkup("**refreshed every week on Sunday**, reverting"),
        ).toEqual([
            { text: "refreshed every week on Sunday", style: "strong" },
            { text: ", reverting" },
        ]);
    });

    it("extracts links", () => {
        expect(
            parseInlineMarkup(
                "shared on the [Arches Community Forum](https://community.archesproject.org/) using",
            ),
        ).toEqual([
            { text: "shared on the " },
            {
                text: "Arches Community Forum",
                url: "https://community.archesproject.org/",
            },
            { text: " using" },
        ]);
    });

    it("supports translations that reorder the marked-up phrases", () => {
        expect(parseInlineMarkup("*GEMET* et *AAT* sont verrouillés.")).toEqual(
            [
                { text: "GEMET", style: "emphasis" },
                { text: " et " },
                { text: "AAT", style: "emphasis" },
                { text: " sont verrouillés." },
            ],
        );
    });
});
