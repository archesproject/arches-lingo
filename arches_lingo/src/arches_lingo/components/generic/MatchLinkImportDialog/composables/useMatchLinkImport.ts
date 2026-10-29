import { onBeforeUnmount, ref } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import {
    fetchMatchLinkImport,
    previewMatchLinkImport,
    startMatchLinkImport,
} from "@/arches_lingo/api.ts";
import {
    MATCH_LINK_IMPORT_COMPLETE_STATUS,
    MATCH_LINK_IMPORT_IN_PROGRESS_STATUSES,
    MATCH_LINK_IMPORT_MAX_FAILED_POLLS,
    MATCH_LINK_IMPORT_POLL_INTERVAL_MS,
    OUTCOME_ADD,
} from "@/arches_lingo/components/generic/MatchLinkImportDialog/utils.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    ERROR,
    SUCCESS,
    WARN,
} from "@/arches_lingo/constants.ts";

import type { Ref } from "vue";
import type {
    MatchLinkImportPreview,
    MatchLinkImportRecord,
} from "@/arches_lingo/components/generic/MatchLinkImportDialog/types.ts";

export function useMatchLinkImport(schemeId?: string): {
    preview: Ref<MatchLinkImportPreview | null>;
    previewErrorMessage: Ref<string | null>;
    isPreviewing: Ref<boolean>;
    isApplying: Ref<boolean>;
    finishedImport: Ref<MatchLinkImportRecord | null>;
    previewFile: (file: File | null) => Promise<void>;
    applyImport: () => Promise<void>;
} {
    const { $gettext, $ngettext } = useGettext();
    const toast = useToast();

    const selectedFile = ref<File | null>(null);
    const preview = ref<MatchLinkImportPreview | null>(null);
    const previewErrorMessage = ref<string | null>(null);
    const isPreviewing = ref(false);
    const isApplying = ref(false);
    const finishedImport = ref<MatchLinkImportRecord | null>(null);
    let isUnmounted = false;

    onBeforeUnmount(() => {
        isUnmounted = true;
    });

    async function previewFile(file: File | null): Promise<void> {
        selectedFile.value = file;
        preview.value = null;
        previewErrorMessage.value = null;
        finishedImport.value = null;
        if (!file) return;

        isPreviewing.value = true;
        try {
            preview.value = await previewMatchLinkImport(file, schemeId);
        } catch (error) {
            previewErrorMessage.value =
                error instanceof Error && error.message
                    ? error.message
                    : $gettext("The file could not be checked.");
        } finally {
            isPreviewing.value = false;
        }
    }

    async function applyImport(): Promise<void> {
        if (!selectedFile.value) return;
        isApplying.value = true;
        try {
            const startedImport = await startMatchLinkImport(
                selectedFile.value,
                schemeId,
            );
            const completedImport = await waitForImport(startedImport);
            if (completedImport) reportFinishedImport(completedImport);
        } catch (error) {
            toast.add({
                severity: ERROR,
                life: DEFAULT_ERROR_TOAST_LIFE,
                summary: $gettext("Unable to import match links"),
                detail: error instanceof Error ? error.message : undefined,
            });
        } finally {
            isApplying.value = false;
        }
    }

    async function waitForImport(
        matchLinkImport: MatchLinkImportRecord,
    ): Promise<MatchLinkImportRecord | null> {
        let currentImport = matchLinkImport;
        let failedPollCount = 0;
        while (
            MATCH_LINK_IMPORT_IN_PROGRESS_STATUSES.includes(
                currentImport.status,
            )
        ) {
            await new Promise((resolve) =>
                setTimeout(resolve, MATCH_LINK_IMPORT_POLL_INTERVAL_MS),
            );
            if (isUnmounted) return null;
            try {
                currentImport = await fetchMatchLinkImport(currentImport.id);
                failedPollCount = 0;
            } catch {
                // The import carries on without the dialog, so a lost status
                // check is not reported as a failed import.
                failedPollCount += 1;
                if (failedPollCount >= MATCH_LINK_IMPORT_MAX_FAILED_POLLS) {
                    toast.add({
                        severity: WARN,
                        life: DEFAULT_ERROR_TOAST_LIFE,
                        summary: $gettext(
                            "Unable to check on the match link import",
                        ),
                        detail: $gettext(
                            "It may still be running. You will be notified when it finishes.",
                        ),
                    });
                    return null;
                }
            }
        }
        return currentImport;
    }

    function reportFinishedImport(
        matchLinkImport: MatchLinkImportRecord,
    ): void {
        if (matchLinkImport.status !== MATCH_LINK_IMPORT_COMPLETE_STATUS) {
            toast.add({
                severity: ERROR,
                life: DEFAULT_ERROR_TOAST_LIFE,
                summary: $gettext("The match link import failed"),
                detail: matchLinkImport.error_message,
            });
            return;
        }
        finishedImport.value = matchLinkImport;
        const addedCount = matchLinkImport.outcome_counts[OUTCOME_ADD] ?? 0;
        toast.add({
            severity: matchLinkImport.error_message ? WARN : SUCCESS,
            life: matchLinkImport.error_message
                ? DEFAULT_ERROR_TOAST_LIFE
                : DEFAULT_TOAST_LIFE,
            summary: $ngettext(
                "%{count} match link added",
                "%{count} match links added",
                addedCount,
                { count: String(addedCount) },
            ),
            detail: matchLinkImport.error_message || undefined,
        });
    }

    return {
        preview,
        previewErrorMessage,
        isPreviewing,
        isApplying,
        finishedImport,
        previewFile,
        applyImport,
    };
}
