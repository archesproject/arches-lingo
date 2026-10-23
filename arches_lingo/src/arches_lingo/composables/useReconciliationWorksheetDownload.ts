import { ref } from "vue";

import { storeToRefs } from "pinia";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import { downloadReconciliationWorksheet } from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { saveBlobAsFile } from "@/arches_lingo/utils.ts";

import type { ReconciliationWorksheetScope } from "@/arches_lingo/types.ts";

const CSV_EXTENSION = ".csv";

export function useReconciliationWorksheetDownload() {
    const { $gettext } = useGettext();
    const toast = useToast();
    const { selectedLanguage } = storeToRefs(useLanguageStore());

    const isDownloading = ref(false);

    async function downloadWorksheet(
        scope: ReconciliationWorksheetScope,
        requestedFilename?: string,
    ): Promise<boolean> {
        isDownloading.value = true;
        try {
            const worksheet = await downloadReconciliationWorksheet(
                scope,
                selectedLanguage.value.code,
            );
            saveBlobAsFile(worksheet, worksheetFilename(requestedFilename));
            return true;
        } catch (error) {
            toast.add({
                severity: ERROR,
                life: DEFAULT_ERROR_TOAST_LIFE,
                summary: $gettext(
                    "Unable to download the reconciliation worksheet",
                ),
                detail: error instanceof Error ? error.message : undefined,
            });
            return false;
        } finally {
            isDownloading.value = false;
        }
    }

    function worksheetFilename(requestedFilename?: string): string {
        const trimmedFilename = requestedFilename?.trim();
        if (!trimmedFilename) {
            const today = new Date().toISOString().slice(0, 10);
            return `reconciliation-worksheet-${today}.csv`;
        }
        return trimmedFilename.toLowerCase().endsWith(CSV_EXTENSION)
            ? trimmedFilename
            : `${trimmedFilename}${CSV_EXTENSION}`;
    }

    return { isDownloading, downloadWorksheet };
}
