import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import {
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    ERROR,
    SUCCESS,
} from "@/arches_lingo/constants.ts";

export interface ClipboardToastSummaries {
    copiedSummary: string;
    failedSummary: string;
}

export function useCopyToClipboard() {
    const { $gettext } = useGettext();
    const toast = useToast();

    function reportCopyFailure(failedSummary: string): void {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: failedSummary,
            detail: $gettext("Select the text and copy it manually."),
        });
    }

    async function copyToClipboard(
        text: string,
        { copiedSummary, failedSummary }: ClipboardToastSummaries,
    ): Promise<void> {
        // The clipboard API only exists in secure contexts (HTTPS or localhost).
        if (!navigator.clipboard) {
            reportCopyFailure(failedSummary);
            return;
        }
        try {
            await navigator.clipboard.writeText(text);
            toast.add({
                severity: SUCCESS,
                life: DEFAULT_TOAST_LIFE,
                summary: copiedSummary,
            });
        } catch {
            reportCopyFailure(failedSummary);
        }
    }

    return { copyToClipboard };
}
