import { onBeforeUnmount, ref } from "vue";

export function useMediaQuery(query: string) {
    const mediaQueryList = window.matchMedia(query);
    const matches = ref(mediaQueryList.matches);

    function updateMatches(event: MediaQueryListEvent) {
        matches.value = event.matches;
    }

    mediaQueryList.addEventListener("change", updateMatches);
    onBeforeUnmount(() => {
        mediaQueryList.removeEventListener("change", updateMatches);
    });

    return matches;
}
