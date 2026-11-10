import { describe, expect, it, vi } from "vitest";

import {
    buildOutcomeLabels,
    summarizeOutcomeCounts,
} from "@/arches_lingo/components/generic/MatchLinkImportDialog/utils.ts";

describe("summarizeOutcomeCounts", () => {
    it("keeps an apostrophe in an outcome label as plain text", async () => {
        // The real gettext (vitest.setup mocks it), since only it HTML-escapes
        // interpolated values.
        const { createGettext } =
            await vi.importActual<typeof import("vue3-gettext")>(
                "vue3-gettext",
            );
        const gettext = createGettext({ silent: true });
        const $gettext = gettext.$gettext.bind(
            gettext,
        ) as typeof gettext.$gettext;

        const [selfMatchTotal] = summarizeOutcomeCounts(
            $gettext,
            buildOutcomeLabels($gettext),
            { self_match: 2 },
        );

        expect(selfMatchTotal.text).toBe("The concept's own URI: 2");
    });
});
