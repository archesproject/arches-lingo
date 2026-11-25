import { nextTick, ref } from "vue";

import type { Ref } from "vue";

// Module-level singleton: LiveAnnouncer renders these into the app's two live
// regions, so any component can announce without mounting its own region.
const politeMessage = ref("");
const assertiveMessage = ref("");

async function setLiveMessage(liveMessage: Ref<string>, message: string) {
    liveMessage.value = "";
    await nextTick();
    liveMessage.value = message;
}

export function useAnnouncer() {
    async function announce(
        message: string,
        { isAssertive = false }: { isAssertive?: boolean } = {},
    ) {
        await setLiveMessage(
            isAssertive ? assertiveMessage : politeMessage,
            message,
        );
    }

    return { politeMessage, assertiveMessage, announce };
}

// Screen readers ignore the app's regions while a modal is open, so
// components that can render inside one need a region of their own.
export function useLocalAnnouncer() {
    const localMessage = ref("");

    async function announceLocally(message: string) {
        await setLiveMessage(localMessage, message);
    }

    return { localMessage, announceLocally };
}
