<script setup lang="ts">
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import { useReconciliationWorksheetDownload } from "@/arches_lingo/composables/useReconciliationWorksheetDownload.ts";

import type { ReconciliationWorksheetScope } from "@/arches_lingo/types.ts";

const { scope } = defineProps<{
    scope: ReconciliationWorksheetScope;
}>();

const { $gettext } = useGettext();
const { isDownloading, downloadWorksheet } =
    useReconciliationWorksheetDownload();
</script>

<template>
    <Button
        icon="pi pi-file-export"
        size="small"
        text
        :label="$gettext('Reconciliation worksheet')"
        :aria-label="
            $gettext('Download a reconciliation worksheet for OpenRefine')
        "
        :loading="isDownloading"
        @click="downloadWorksheet(scope)"
    />
</template>
