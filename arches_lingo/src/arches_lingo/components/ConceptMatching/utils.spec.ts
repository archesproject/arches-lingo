import { describe, expect, it } from "vitest";

import {
    SIGNAL_EXACT_LABEL,
    SIGNAL_SHARED_IDENTIFIER,
    SIGNAL_TRIGRAM,
} from "@/arches_lingo/components/ConceptMatching/constants.ts";
import {
    buildSignalList,
    candidateStatusFromRoute,
    describeSkippedReasons,
    isRunUnfinished,
    splitElapsedSeconds,
} from "@/arches_lingo/components/ConceptMatching/utils.ts";

import type { ConceptMatchRun } from "@/arches_lingo/types.ts";

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
        expect(splitElapsedSeconds(-500)).toEqual({ minutes: 0, seconds: 0 });
    });
});

describe("candidateStatusFromRoute", () => {
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
