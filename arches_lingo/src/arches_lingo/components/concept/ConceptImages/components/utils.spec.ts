import { describe, expect, it, vi } from "vitest";

import {
    PLACEHOLDER_ALT_TEXT,
    getDigitalObjectImageAlt,
} from "@/arches_lingo/components/concept/ConceptImages/components/utils.ts";

import type { DigitalObjectInstance } from "@/arches_lingo/types.ts";

vi.mock("arches", () => ({ default: { urls: { url_subpath: "/" } } }));
vi.mock("@/arches_lingo/api.ts", () => ({}));

function buildDigitalObject(
    fileMetadata: Record<string, unknown>,
): DigitalObjectInstance {
    return {
        aliased_data: {
            content: {
                aliased_data: {
                    content: {
                        node_value: [
                            {
                                name: "IMG_0042.jpg",
                                url: "/files/IMG_0042.jpg",
                                ...fileMetadata,
                            },
                        ],
                    },
                },
            },
        },
    } as unknown as DigitalObjectInstance;
}

describe("getDigitalObjectImageAlt", () => {
    it("reads the alt text in the given language", () => {
        const digitalObject = buildDigitalObject({
            altText: {
                en: { value: "A red vase", direction: "ltr" },
                ar: { value: "مزهرية حمراء", direction: "rtl" },
            },
        });

        expect(getDigitalObjectImageAlt(digitalObject, "ar")).toBe(
            "مزهرية حمراء",
        );
    });

    it("falls back to the title in the same language", () => {
        const digitalObject = buildDigitalObject({
            altText: { en: { value: "", direction: "ltr" } },
            title: { en: { value: "Vase, 1890", direction: "ltr" } },
        });

        expect(getDigitalObjectImageAlt(digitalObject, "en")).toBe(
            "Vase, 1890",
        );
    });

    it("treats the old placeholder as missing", () => {
        const digitalObject = buildDigitalObject({
            altText: {
                en: { value: PLACEHOLDER_ALT_TEXT, direction: "ltr" },
            },
            title: { en: { value: "Vase, 1890", direction: "ltr" } },
        });

        expect(getDigitalObjectImageAlt(digitalObject, "en")).toBe(
            "Vase, 1890",
        );
    });

    it("reads a plain string left over from older data", () => {
        const digitalObject = buildDigitalObject({ altText: "A red vase" });

        expect(getDigitalObjectImageAlt(digitalObject, "en")).toBe(
            "A red vase",
        );
    });

    it("never falls back to the file name", () => {
        expect(getDigitalObjectImageAlt(buildDigitalObject({}), "en")).toBe("");
    });
});
