import { inject, markRaw, type MaybeRefOrGetter, toValue } from "vue";
import { useGettext } from "vue3-gettext";
import EditLog from "@/arches_lingo/components/generic/EditLog/EditLog.vue";
import { openPanelComponentKey } from "@/arches_lingo/constants.ts";

export function useEditLog(graphSlug: MaybeRefOrGetter<string>) {
    const openPanelComponent = inject(openPanelComponentKey);
    const { $gettext } = useGettext();

    function openEditLog() {
        openPanelComponent?.(
            markRaw(EditLog),
            "EditLog",
            $gettext("Edit History"),
            toValue(graphSlug),
        );
    }

    return { openEditLog };
}
