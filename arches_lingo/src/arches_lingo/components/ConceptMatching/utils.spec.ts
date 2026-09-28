import { describe, expect, it } from "vitest";

import {
    SIGNAL_EXACT_LABEL,
    SIGNAL_SHARED_IDENTIFIER,
    SIGNAL_TRIGRAM,
} from "@/arches_lingo/components/ConceptMatching/constants.ts";
import {
    buildPreselectedConcept,
    buildSignalList,
    candidateStatusFromRoute,
    describeSkippedReasons,
    estimateDurationSpan,
    estimateFuzzyRunSeconds,
    labelsInScope,
    isRunUnfinished,
    resolveMergeSides,
    splitElapsedSeconds,
} from "@/arches_lingo/components/ConceptMatching/utils.ts";

import type {
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
    const conceptA = conceptSummary("aaa", "Trumpets");
    const conceptB = conceptSummary("bbb", "Trumpet");

    it("reads the survivor from whichever side was not absorbed", () => {
        const sides = resolveMergeSides(conceptA, conceptB, "bbb");

        expect(sides.survivor.id).toEqual("aaa");
        expect(sides.absorbed.id).toEqual("bbb");
    });

    it("works whichever way round the pair is stored", () => {
        const sides = resolveMergeSides(conceptA, conceptB, "aaa");

        expect(sides.survivor.id).toEqual("bbb");
        expect(sides.absorbed.id).toEqual("aaa");
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

describe("describeSkippedReasons", () => {
    it("lists each reason in the reader's language", () => {
        expect(
            describeSkippedReasons(
                { missing_uri: 2, not_editable: 1 },
                (reason, count) => `${count} ${reason}`,
                "en",
            ),
        ).toEqual("2 missing_uri and 1 not_editable");
    });
});

describe("splitElapsedSeconds", () => {
    it("splits minutes from the remaining seconds", () => {
        expect(splitElapsedSeconds(1329)).toEqual({ minutes: 22, seconds: 9 });
    });

    it("never counts backwards", () => {
        // A client whose clock disagrees with the server's must not be shown a
        // negative age -- the elapsed time it is given is the server's own.
        expect(splitElapsedSeconds(-500)).toEqual({ minutes: 0, seconds: 0 });
    });
});

describe("labelsInScope", () => {
    const labelsByScheme = { aat: 522611, fish: 8167, tgn: 201112 };

    it("counts every label when no scheme is chosen", () => {
        // Including labels belonging to no scheme, which an unscoped run compares.
        expect(labelsInScope([], 740559, labelsByScheme)).toBe(740559);
    });

    it("adds up only the schemes chosen", () => {
        expect(labelsInScope(["aat", "fish"], 740559, labelsByScheme)).toBe(
            530778,
        );
    });

    it("ignores a scheme it has no count for", () => {
        expect(labelsInScope(["aat", "gone"], 740559, labelsByScheme)).toBe(
            522611,
        );
    });
});

describe("estimateFuzzyRunSeconds", () => {
    // Every run actually measured. What the interface promises is the span
    // rather than the figure, so what is checked here is that the span still
    // contains the real timing: if a change to the constants breaks this, the
    // warning has started misleading people.
    it.each([
        ["one small scheme", 8167, 32],
        ["a medium scheme", 201112, 272],
        ["most of the corpus", 530778, 1080],
        ["the whole corpus", 740559, 1357],
    ])("brackets what %s measured", (_case, labels, measuredSeconds) => {
        const estimated = estimateFuzzyRunSeconds(labels);
        expect(measuredSeconds).toBeGreaterThanOrEqual(estimated * 0.7);
        expect(measuredSeconds).toBeLessThanOrEqual(estimated * 1.4);
    });
});

describe("estimateDurationSpan", () => {
    it("does not put a number on a search that is nearly instant", () => {
        expect(estimateDurationSpan(1000)).toEqual({ kind: "brief" });
    });

    it("gives a span rather than a figure it cannot justify", () => {
        expect(estimateDurationSpan(530778)).toEqual({
            kind: "minutes",
            lowMinutes: 11,
            highMinutes: 23,
        });
    });

    it("stops pretending to be precise once it is very long", () => {
        expect(estimateDurationSpan(5000000)).toEqual({ kind: "overAnHour" });
    });
});

describe("candidateStatusFromRoute", () => {
    // The filter offers four queues, and every one of them has to survive the
    // round trip through the address. Only two did once, and the two that did
    // not silently showed the outstanding pairs instead.
    it.each([
        ["pending", "pending"],
        ["dismissed", "dismissed"],
        ["linked", "linked"],
        ["merged", "merged"],
    ])("keeps %s", (rawStatus, expected) => {
        expect(candidateStatusFromRoute(rawStatus)).toBe(expected);
    });

    it.each([
        ["nothing at all", undefined],
        ["an empty string", ""],
        ["a status that does not exist", "abandoned"],
        ["a repeated parameter", ["linked", "merged"]],
    ])("falls back to the queue for %s", (_case, rawStatus) => {
        expect(candidateStatusFromRoute(rawStatus)).toBe("pending");
    });
});
