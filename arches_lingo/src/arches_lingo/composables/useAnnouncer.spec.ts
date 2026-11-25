import { nextTick } from "vue";

import { describe, expect, it } from "vitest";

import {
    useAnnouncer,
    useLocalAnnouncer,
} from "@/arches_lingo/composables/useAnnouncer.ts";

describe("useAnnouncer", () => {
    it("routes polite and assertive messages to separate regions", async () => {
        const { announce, politeMessage, assertiveMessage } = useAnnouncer();

        await announce("Saved");
        await announce("Save failed", { isAssertive: true });

        expect(politeMessage.value).toBe("Saved");
        expect(assertiveMessage.value).toBe("Save failed");
    });

    it("clears before repeating a message so it is announced again", async () => {
        const { announce, politeMessage } = useAnnouncer();
        await announce("Loaded");

        const repeated = announce("Loaded");
        expect(politeMessage.value).toBe("");

        await repeated;
        await nextTick();
        expect(politeMessage.value).toBe("Loaded");
    });
});

describe("useLocalAnnouncer", () => {
    it("keeps its message separate from the app's regions", async () => {
        const { politeMessage } = useAnnouncer();
        const { announceLocally, localMessage } = useLocalAnnouncer();
        await useAnnouncer().announce("App message");

        await announceLocally("3 results found");

        expect(localMessage.value).toBe("3 results found");
        expect(politeMessage.value).toBe("App message");
    });
});
