import {
    PLACEHOLDER_ALT_TEXT,
    getDigitalObjectImageAlt,
    getDigitalObjectImageTitle,
} from "@/arches_lingo/components/concept/ConceptImages/components/utils.ts";

import type { DigitalObjectInstance } from "@/arches_lingo/types.ts";

// The upload helpers in utils.ts pull in the API and a Pinia store; the alt
// text helpers under test need neither.
vi.mock("@/arches_lingo/api.ts", () => ({}));
vi.mock("@/arches_vue_components/stores/useWidgetConfigStore.ts", () => ({
    useWidgetConfigStore: vi.fn(),
}));

function buildDigitalObject({
    altText,
    titleNodeValue,
    titleDisplayValue = "",
    fileName = "IMG_0001.jpg",
}: {
    altText?: unknown;
    titleNodeValue?: unknown;
    titleDisplayValue?: string;
    fileName?: string;
}): DigitalObjectInstance {
    return {
        aliased_data: {
            name:
                titleNodeValue === undefined
                    ? undefined
                    : {
                          aliased_data: {
                              name_content: {
                                  display_value: titleDisplayValue,
                                  node_value: titleNodeValue,
                                  details: [],
                              },
                          },
                      },
            content: {
                aliased_data: {
                    content: {
                        display_value: "",
                        node_value: [{ name: fileName, altText }],
                        details: [],
                    },
                },
            },
        },
    } as unknown as DigitalObjectInstance;
}

describe("getDigitalObjectImageAlt", () => {
    it("reads the alt text for the requested language", () => {
        const resource = buildDigitalObject({
            altText: {
                en: { value: "A red vase", direction: "ltr" },
                fr: { value: "Un vase rouge", direction: "ltr" },
            },
        });

        expect(getDigitalObjectImageAlt(resource, "fr")).toBe("Un vase rouge");
    });

    it("falls back to the localized title when the language has no alt text", () => {
        const resource = buildDigitalObject({
            altText: {
                en: { value: "A red vase", direction: "ltr" },
                fr: { value: "", direction: "ltr" },
            },
            titleNodeValue: {
                en: { value: "Vase", direction: "ltr" },
                fr: { value: "Vase rouge", direction: "ltr" },
            },
        });

        expect(getDigitalObjectImageAlt(resource, "fr")).toBe("Vase rouge");
    });

    it("treats the legacy placeholder as absent", () => {
        const resource = buildDigitalObject({
            altText: {
                en: { value: PLACEHOLDER_ALT_TEXT, direction: "ltr" },
            },
            titleNodeValue: "Vase",
        });

        expect(getDigitalObjectImageAlt(resource, "en")).toBe("Vase");
    });

    it("accepts a legacy plain-string alt text", () => {
        const resource = buildDigitalObject({ altText: "A red vase" });

        expect(getDigitalObjectImageAlt(resource, "en")).toBe("A red vase");
    });

    it("never falls back to the file name", () => {
        const resource = buildDigitalObject({ altText: undefined });

        expect(getDigitalObjectImageAlt(resource, "en")).toBe("");
    });
});

describe("getDigitalObjectImageTitle", () => {
    it("falls back to the display value when the language has no title", () => {
        const resource = buildDigitalObject({
            titleNodeValue: { en: { value: "Vase", direction: "ltr" } },
            titleDisplayValue: "Vase",
        });

        expect(getDigitalObjectImageTitle(resource, "de")).toBe("Vase");
    });
});
