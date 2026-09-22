import { describe, expect, it } from "vitest";

import {
    SIGNAL_EXACT_LABEL,
    SIGNAL_SHARED_IDENTIFIER,
    SIGNAL_TRIGRAM,
} from "@/arches_lingo/components/concept-matching/constants.ts";
import {
    buildPreselectedConcept,
    buildSignalList,
    describeMatchReason,
    describeSkippedReasons,
    formatElapsed,
    isRunUnfinished,
    resolveMergeSides,
} from "@/arches_lingo/components/concept-matching/utils.ts";

import type {
    ConceptMatchCandidate,
    ConceptMatchRun,
    MatchedConceptSummary,
} from "@/arches_lingo/types.ts";

function conceptSummary(id: string, value: string): MatchedConceptSummary {
    return {
        id,
        labels: [
            {
                value,
                language_id: "en",
                valuetype_id: "prefLabel",
            },
        ],
        scheme_id: "scheme-1",
        scheme_name: "Test Scheme",
    } as MatchedConceptSummary;
}

function candidate(
    overrides: Partial<ConceptMatchCandidate> = {},
): ConceptMatchCandidate {
    return {
        id: 1,
        score: 1.0,
        signal: SIGNAL_EXACT_LABEL,
        evidence: "trumpets",
        status: "pending",
        concept_a: conceptSummary("aaa", "Trumpets"),
        concept_b: conceptSummary("bbb", "Trumpet"),
        is_cross_scheme: false,
        ...overrides,
    } as ConceptMatchCandidate;
}

function run(overrides: Partial<ConceptMatchRun> = {}): ConceptMatchRun {
    return {
        id: 1,
        status: "complete",
        created: "2026-09-22T00:00:00Z",
        finished: null,
        parameters: {},
        candidate_count: 0,
        pending_count: 0,
        error_message: "",
        ...overrides,
    } as ConceptMatchRun;
}

// The translate stub renders the template so the branch's wording is asserted
// rather than just which branch was taken.
function translate(message: string, options: Record<string, string>) {
    return message.replace(
        /%\{(\w+)\}/g,
        (_match, key: string) => options[key] ?? "",
    );
}

describe("buildSignalList", () => {
    it("orders signals strongest first, as the server resolves them", () => {
        expect(
            buildSignalList({
                compareUris: true,
                compareLabels: true,
                compareSimilarLabels: true,
            }),
        ).toEqual([
            SIGNAL_SHARED_IDENTIFIER,
            SIGNAL_EXACT_LABEL,
            SIGNAL_TRIGRAM,
        ]);
    });

    it("leaves out what was not asked for", () => {
        expect(
            buildSignalList({
                compareUris: false,
                compareLabels: true,
                compareSimilarLabels: false,
            }),
        ).toEqual([SIGNAL_EXACT_LABEL]);
    });

    it("returns nothing when every signal is off", () => {
        expect(
            buildSignalList({
                compareUris: false,
                compareLabels: false,
                compareSimilarLabels: false,
            }),
        ).toEqual([]);
    });
});

describe("isRunUnfinished", () => {
    it("treats a queued or running run as unfinished", () => {
        expect(isRunUnfinished(run({ status: "pending" }))).toBe(true);
        expect(isRunUnfinished(run({ status: "running" }))).toBe(true);
    });

    it("treats a settled run as finished, however it settled", () => {
        expect(isRunUnfinished(run({ status: "complete" }))).toBe(false);
        expect(isRunUnfinished(run({ status: "failed" }))).toBe(false);
    });
});

describe("resolveMergeSides", () => {
    it("reads the survivor from whichever side was not absorbed", () => {
        const pair = candidate();

        expect(resolveMergeSides(pair, "bbb").survivor.id).toEqual("aaa");
        expect(resolveMergeSides(pair, "bbb").absorbed.id).toEqual("bbb");
    });

    it("works whichever way round the pair is stored", () => {
        const pair = candidate();

        expect(resolveMergeSides(pair, "aaa").survivor.id).toEqual("bbb");
        expect(resolveMergeSides(pair, "aaa").absorbed.id).toEqual("aaa");
    });
});

describe("buildPreselectedConcept", () => {
    it("carries the id and labels the merge dialog reads", () => {
        const preselected = buildPreselectedConcept(
            conceptSummary("aaa", "Trumpets"),
        );

        expect(preselected.id).toEqual("aaa");
        expect(preselected.labels[0].value).toEqual("Trumpets");
        expect(preselected.parents).toEqual([]);
        expect(preselected.polyhierarchical).toBe(false);
    });
});

describe("describeMatchReason", () => {
    it("names the shared URI", () => {
        expect(
            describeMatchReason(
                candidate({
                    signal: SIGNAL_SHARED_IDENTIFIER,
                    evidence: "https://example.org/1",
                }),
                translate,
            ),
        ).toEqual("Same URI: https://example.org/1");
    });

    it("reports the similarity for a fuzzy match", () => {
        expect(
            describeMatchReason(
                candidate({
                    signal: SIGNAL_TRIGRAM,
                    score: 0.8712,
                    evidence: "trumpets ~ trumpeters",
                }),
                translate,
            ),
        ).toEqual("Similar labels (0.87): trumpets ~ trumpeters");
    });

    it("names the shared label otherwise", () => {
        expect(describeMatchReason(candidate(), translate)).toEqual(
            "Same label: trumpets",
        );
    });
});

describe("describeSkippedReasons", () => {
    it("names each reason so a reviewer can act on it", () => {
        expect(
            describeSkippedReasons(
                { missing_uri: 2, not_editable: 1 },
                {
                    missing_uri: "no URI to point at",
                    not_editable: "neither concept can be edited",
                },
            ),
        ).toEqual("2 (no URI to point at), 1 (neither concept can be edited)");
    });

    it("falls back to the raw reason when it has no wording yet", () => {
        expect(describeSkippedReasons({ something_new: 1 }, {})).toEqual(
            "1 (something_new)",
        );
    });
});

describe("formatElapsed", () => {
    function translate(message: string, options: Record<string, string>) {
        return message.replace(
            /%\{(\w+)\}/g,
            (_match, key: string) => options[key],
        );
    }

    it("reads in seconds below a minute", () => {
        expect(formatElapsed(45, translate)).toBe("45s");
    });

    it("reads in minutes and padded seconds above one", () => {
        expect(formatElapsed(1329, translate)).toBe("22m 09s");
    });

    it("keeps a whole minute from losing its seconds", () => {
        expect(formatElapsed(120, translate)).toBe("2m 00s");
    });

    it("never counts backwards", () => {
        // A client whose clock disagrees with the server's must not be shown a
        // negative age -- the elapsed time it is given is the server's own.
        expect(formatElapsed(-500, translate)).toBe("0s");
    });
});
