<script setup lang="ts">
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import { getSearchExportFile } from "@/arches_lingo/api.ts";

const toast = useToast();
const { $gettext } = useGettext();

const { link } = defineProps<{
    link: string; // pk for a SearchExportHistory instance
}>();

async function downloadZipFile(link: string) {
    await getSearchExportFile(link).then((response) => {
        if (response.url) {
            window.open(response.url);
        } else {
            toast.add({
                severity: "error",
                summary: $gettext("Download Failed"),
                detail: $gettext("The requested file could not be downloaded."),
            });
        }
    });
}
</script>

<template>
    <Button
        icon="pi pi-download"
        :label="$gettext('Download Zip File')"
        size="small"
        @click="downloadZipFile(link)"
    />
</template>
