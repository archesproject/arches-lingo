import {
    CONCEPT_ICON,
    GUIDE_TERM_ICON,
    SCHEME_ICON,
    TOP_CONCEPT_ICON,
} from "@/arches_lingo/constants.ts";
import {
    checkDeepEquality,
    dataIsConcept,
    dataIsScheme,
    extractDescriptors,
    generateConditionId,
    getAutonym,
    getConceptIcon,
    getIconLabel,
    getItemIcon,
    getParentLabels,
    getStatementText,
    sortItemsByLabel,
    treeFromSchemes,
} from "@/arches_lingo/utils.ts";
import schemesFixture from "./fixtures/test_scheme.json";

import type { Language } from "@/arches_component_lab/types.ts";
import type {
    Concept,
    IconLabels,
    ResourceInstanceResult,
    Scheme,
    SchemeStatement,
    SearchResultItem,
} from "@/arches_lingo/types";

const ENGLISH: Language = {
    code: "en",
    default_direction: "ltr",
    id: 1,
    isdefault: true,
    name: "English",
    scope: "system",
};

const iconLabels: IconLabels = {
    concept: "Concept",
    guideTerm: "Guide Term",
    scheme: "Scheme",
    topConcept: "Top Concept",
};

describe("Duck-typing helpers", () => {
    it("Should distinguish schemes from concepts", () => {
        const scheme = schemesFixture["schemes"][0];
        expect(dataIsScheme(scheme)).toBeTruthy();
        expect(dataIsConcept(scheme)).toBeFalsy();
    });
});

describe("Build scheme hierarchy", () => {
    it("Should shape schemes into TreeNodes", () => {
        const nodes = treeFromSchemes(
            schemesFixture["schemes"] as Scheme[],
            ENGLISH,
            ENGLISH,
            iconLabels,
            null,
        );
        const schemeNode = nodes[0];
        expect(schemeNode.label).toEqual("Test Scheme");
        expect(schemeNode.iconLabel).toEqual("Scheme");
        expect(schemeNode.data.top_concepts.length).toEqual(2);

        const topConcept = schemeNode.data.top_concepts[0];
        expect(topConcept.labels[0].value).toEqual("Concept 1");
        expect(topConcept.narrower.length).toEqual(4);
    });
    it("Should hide other top concepts when focusing child of another", () => {
        const nodesBeforeFocus = treeFromSchemes(
            schemesFixture["schemes"] as Scheme[],
            ENGLISH,
            ENGLISH,
            iconLabels,
            null,
        );
        const focusedNode = nodesBeforeFocus[0].children![0].children!.find(
            (n) => n.data.labels[0].value === "Concept 2",
        )!;
        const nodesAfterFocus = treeFromSchemes(
            schemesFixture["schemes"] as Scheme[],
            ENGLISH,
            ENGLISH,
            iconLabels,
            focusedNode as unknown as string,
        );
        const scheme = nodesAfterFocus[0];
        expect(scheme.children!.length).toEqual(2); // Only Concept 1 and Concept 2
    });

    it("Should use guide term icon for guide term concepts", () => {
        const nodes = treeFromSchemes(
            schemesFixture["schemes"] as Scheme[],
            ENGLISH,
            ENGLISH,
            iconLabels,
            null,
        );
        const schemeNode = nodes[0];

        // Scheme node should have scheme icon
        expect(schemeNode.icon).toEqual(SCHEME_ICON);

        // Top concept (Concept 1) is not a guide term
        const topConceptNode = schemeNode.children![0];
        expect(topConceptNode.icon).toEqual(CONCEPT_ICON);

        // Concept 3 is a guide term in the fixture
        const concept3Node = topConceptNode.children!.find(
            (n) => n.data.labels[0].value === "Concept 3",
        )!;
        expect(concept3Node.icon).toEqual(GUIDE_TERM_ICON);

        // Concept 2 is not a guide term
        const concept2Node = topConceptNode.children!.find(
            (n) => n.data.labels[0].value === "Concept 2",
        )!;
        expect(concept2Node.icon).toEqual(CONCEPT_ICON);
    });

    it("Should focus a scheme when its id is the focused key", () => {
        const schemeId = (schemesFixture["schemes"][0] as Scheme).id;
        const focusedNodes = treeFromSchemes(
            schemesFixture["schemes"] as Scheme[],
            ENGLISH,
            ENGLISH,
            iconLabels,
            schemeId,
        );
        expect(focusedNodes.length).toEqual(1);
        expect(focusedNodes[0].data.id).toEqual(schemeId);
    });
});

describe("getConceptIcon", () => {
    it("Should return guide term icon for guide term items", () => {
        expect(getConceptIcon({ guide_term: true })).toEqual(GUIDE_TERM_ICON);
    });

    it("Should return top concept icon for top concept items", () => {
        expect(getConceptIcon({ top_concept: true })).toEqual(TOP_CONCEPT_ICON);
    });

    it("Should return default concept icon for regular concepts", () => {
        expect(getConceptIcon({ guide_term: false })).toEqual(CONCEPT_ICON);
        expect(getConceptIcon({})).toEqual(CONCEPT_ICON);
    });
});

describe("getItemIcon", () => {
    it("Should return scheme icon for schemes", () => {
        const scheme = schemesFixture["schemes"][0] as Scheme;
        expect(getItemIcon(scheme)).toEqual(SCHEME_ICON);
    });

    it("Should return concept icon for non-guide-term concepts", () => {
        const concept: Concept = {
            id: "test",
            labels: [],
            narrower: [],
            guide_term: false,
        };
        expect(getItemIcon(concept)).toEqual(CONCEPT_ICON);
    });
});

describe("getIconLabel", () => {
    it("Should return scheme label for schemes", () => {
        const scheme = schemesFixture["schemes"][0] as Scheme;
        expect(getIconLabel(scheme, iconLabels)).toEqual("Scheme");
    });

    it("Should return guide term label for guide term concepts", () => {
        const guideTerm: Concept = {
            id: "test",
            labels: [],
            narrower: [],
            guide_term: true,
        };
        expect(getIconLabel(guideTerm, iconLabels)).toEqual("Guide Term");
    });

    it("Should return top concept label for top concepts", () => {
        const topConcept: Concept = {
            id: "test",
            labels: [],
            narrower: [],
            top_concept: true,
        };
        expect(getIconLabel(topConcept, iconLabels)).toEqual("Top Concept");
    });

    it("Should return concept label for regular concepts", () => {
        const concept: Concept = {
            id: "test",
            labels: [],
            narrower: [],
        };
        expect(getIconLabel(concept, iconLabels)).toEqual("Concept");
    });
});

describe("sortItemsByLabel", () => {
    const englishLabel = (value: string) => ({
        language_id: "en",
        value,
        valuetype_id: "prefLabel",
    });

    it("Should sort concepts alphabetically in ascending order", () => {
        const concepts: Concept[] = [
            { id: "1", labels: [englishLabel("Zebra")], narrower: [] },
            { id: "2", labels: [englishLabel("Apple")], narrower: [] },
            { id: "3", labels: [englishLabel("Mango")], narrower: [] },
        ];
        const sorted = sortItemsByLabel(concepts, "en", "en");
        expect(sorted.map((concept) => concept.id)).toEqual(["2", "3", "1"]);
    });

    it("Should sort in descending order when sortAscending is false", () => {
        const concepts: Concept[] = [
            { id: "1", labels: [englishLabel("Apple")], narrower: [] },
            { id: "2", labels: [englishLabel("Zebra")], narrower: [] },
        ];
        const sorted = sortItemsByLabel(concepts, "en", "en", false);
        expect(sorted.map((concept) => concept.id)).toEqual(["2", "1"]);
    });

    it("Should pin a specified item first regardless of sort order", () => {
        const concepts: Concept[] = [
            { id: "1", labels: [englishLabel("Zebra")], narrower: [] },
            { id: "2", labels: [englishLabel("Apple")], narrower: [] },
        ];
        const sorted = sortItemsByLabel(concepts, "en", "en", true, "1");
        expect(sorted[0].id).toEqual("1");
    });

    it("Should not mutate the original array", () => {
        const concepts: Concept[] = [
            { id: "1", labels: [englishLabel("Zebra")], narrower: [] },
            { id: "2", labels: [englishLabel("Apple")], narrower: [] },
        ];
        const originalOrder = ["1", "2"];
        sortItemsByLabel(concepts, "en", "en");
        expect(concepts.map((concept) => concept.id)).toEqual(originalOrder);
    });
});

describe("checkDeepEquality", () => {
    it("Should return true for identical primitives", () => {
        expect(checkDeepEquality(1, 1)).toBe(true);
        expect(checkDeepEquality("a", "a")).toBe(true);
        expect(checkDeepEquality(null, null)).toBe(true);
    });

    it("Should return false for different primitives", () => {
        expect(checkDeepEquality(1, 2)).toBe(false);
        expect(checkDeepEquality("a", "b")).toBe(false);
    });

    it("Should return false when types differ", () => {
        expect(checkDeepEquality(1, "1")).toBe(false);
    });

    it("Should return true for deeply equal objects", () => {
        expect(checkDeepEquality({ a: { b: 1 } }, { a: { b: 1 } })).toBe(true);
    });

    it("Should return false for objects with different values", () => {
        expect(checkDeepEquality({ a: 1 }, { a: 2 })).toBe(false);
    });

    it("Should return true for equal arrays", () => {
        expect(checkDeepEquality([1, 2, 3], [1, 2, 3])).toBe(true);
    });

    it("Should return false for arrays of different length", () => {
        expect(checkDeepEquality([1, 2], [1, 2, 3])).toBe(false);
    });

    it("Should return false for arrays with different elements", () => {
        expect(checkDeepEquality([1, 2], [1, 3])).toBe(false);
    });
});

describe("getParentLabels", () => {
    const englishLabel = (value: string) => ({
        language_id: "en",
        value,
        valuetype_id: "prefLabel",
    });

    it("Should return empty string when parents is empty", () => {
        const item: SearchResultItem = {
            id: "1",
            labels: [],
            parents: [],
            polyhierarchical: false,
        };
        expect(getParentLabels(item, "en", "en")).toEqual("");
    });

    it("Should return empty string when parents array has an empty path", () => {
        const item: SearchResultItem = {
            id: "1",
            labels: [],
            parents: [[]],
            polyhierarchical: false,
        };
        expect(getParentLabels(item, "en", "en")).toEqual("");
    });

    it("Should join parent labels with arrows for a single path", () => {
        const item: SearchResultItem = {
            id: "3",
            labels: [],
            parents: [
                [
                    { id: "1", labels: [englishLabel("Scheme")] },
                    { id: "2", labels: [englishLabel("Parent Concept")] },
                ],
            ],
            polyhierarchical: false,
        };
        expect(getParentLabels(item, "en", "en")).toEqual(
            "Scheme → Parent Concept",
        );
    });

    it("Should use the first parent path when polyhierarchical", () => {
        const item: SearchResultItem = {
            id: "3",
            labels: [],
            parents: [
                [{ id: "1", labels: [englishLabel("Path One")] }],
                [{ id: "2", labels: [englishLabel("Path Two")] }],
            ],
            polyhierarchical: true,
        };
        expect(getParentLabels(item, "en", "en")).toEqual("Path One");
    });
});

describe("extractDescriptors", () => {
    it("Should return empty descriptor when resource is undefined", () => {
        const descriptor = extractDescriptors(undefined, ENGLISH);
        expect(descriptor.name).toEqual("");
        expect(descriptor.description).toEqual("");
        expect(descriptor.language).toEqual("");
    });

    it("Should extract descriptor for the selected language", () => {
        const resource: ResourceInstanceResult = {
            resourceinstanceid: "1",
            descriptors: {
                en: {
                    name: "English Name",
                    description: "English description",
                },
            },
        };
        const descriptor = extractDescriptors(resource, ENGLISH);
        expect(descriptor.name).toEqual("English Name");
        expect(descriptor.description).toEqual("English description");
        expect(descriptor.language).toEqual("en");
    });

    it("Should fall back to first available language when selected language is absent", () => {
        const resource: ResourceInstanceResult = {
            resourceinstanceid: "1",
            descriptors: {
                de: { name: "German Name", description: "German description" },
            },
        };
        const descriptor = extractDescriptors(resource, ENGLISH);
        expect(descriptor.name).toEqual("German Name");
        expect(descriptor.language).toEqual("de");
    });
});

describe("getAutonym", () => {
    it("Should return the autonym for a supported language code", () => {
        // 'en' should return something like 'English' (in English)
        const result = getAutonym("en", "English fallback");
        expect(typeof result).toEqual("string");
        expect(result.length).toBeGreaterThan(0);
    });

    it("Should return the fallback for an unsupported or invalid code", () => {
        const result = getAutonym("xx-invalid-code-zz", "Fallback Value");
        expect(result).toEqual("Fallback Value");
    });
});

describe("getStatementText", () => {
    const makeStatement = (
        content: string,
        language?: string,
    ): SchemeStatement => ({
        aliased_data: {
            statement_content: {
                display_value: content,
                node_value: null,
                details: [],
            },
            statement_language: language
                ? { display_value: language, node_value: [] }
                : undefined,
        },
    });

    it("Should return empty string for empty statements array", () => {
        expect(getStatementText([], "en", "en")).toEqual("");
    });

    it("Should prefer statement in active language", () => {
        const statements = [
            makeStatement("German text", "de"),
            makeStatement("English text", "en"),
        ];
        const result = getStatementText(statements, "en", "de");
        expect(result).toEqual("English text");
    });

    it("Should prefer system language over others when active language is absent", () => {
        const statements = [
            makeStatement("System text", "de"),
            makeStatement("Other text", "fr"),
        ];
        const result = getStatementText(statements, "en", "de");
        expect(result).toEqual("System text");
    });

    it("Should return content from first statement when no language matches", () => {
        const statements = [makeStatement("Only text", "zh")];
        const result = getStatementText(statements, "en", "de");
        expect(result).toEqual("Only text");
    });
});

describe("generateConditionId", () => {
    it("Should return a string starting with cond-", () => {
        const conditionId = generateConditionId();
        expect(conditionId.startsWith("cond-")).toBe(true);
    });

    it("Should return unique IDs on successive calls", () => {
        const firstId = generateConditionId();
        const secondId = generateConditionId();
        expect(firstId).not.toEqual(secondId);
    });
});
