import { storeToRefs } from "pinia";

import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

import type { Labellable } from "@/arches_controlled_lists/types.ts";

export function useLocalizedLabel(): {
    labelOf: (item: Labellable) => string;
} {
    const { selectedLanguage, systemLanguage } =
        storeToRefs(useLanguageStore());

    function labelOf(item: Labellable): string {
        return getItemLabel(
            item,
            selectedLanguage.value.code,
            systemLanguage.value.code,
        ).value;
    }

    return { labelOf };
}
