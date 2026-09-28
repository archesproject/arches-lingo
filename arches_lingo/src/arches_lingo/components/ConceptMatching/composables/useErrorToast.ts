import { useToast } from "primevue/usetoast";

import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";

export function useErrorToast(): {
    reportError: (error: unknown, summary: string) => void;
} {
    const toast = useToast();

    function reportError(error: unknown, summary: string): void {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary,
            detail: error instanceof Error ? error.message : undefined,
        });
    }

    return { reportError };
}
