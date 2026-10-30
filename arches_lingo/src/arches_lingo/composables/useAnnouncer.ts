import { nextTick, ref } from "vue";

// Module-level singleton: LiveAnnouncer renders these into the app's two live
// regions, so any component can announce without mounting its own region.
const politeMessage = ref("");
const assertiveMessage = ref("");

export function useAnnouncer() {
    async function announce(
        message: string,
        { isAssertive = false }: { isAssertive?: boolean } = {},
    ) {
        const liveMessage = isAssertive ? assertiveMessage : politeMessage;
        liveMessage.value = "";
        await nextTick();
        liveMessage.value = message;
    }

    return { politeMessage, assertiveMessage, announce };
}
