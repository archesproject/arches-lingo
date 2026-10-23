<script setup lang="ts">
import { useGettext } from "vue3-gettext";

import FileUpload from "primevue/fileupload";

const FILE_INPUT_ID = "match-link-import-file";

const { isDisabled } = defineProps<{
    isDisabled: boolean;
}>();

const emit = defineEmits<{
    (event: "file-selected", file: File | null): void;
}>();

const { $gettext } = useGettext();

function onFileSelected(event: { files: File[] }): void {
    emit("file-selected", event.files?.[0] ?? null);
}
</script>

<template>
    <div class="match-link-import-upload">
        <label :for="FILE_INPUT_ID">{{
            $gettext("Match links file (CSV)")
        }}</label>
        <p class="help-text">
            {{
                $gettext(
                    "Needs concept_id and match_uri columns. An optional match_type column can be exactMatch (the default), closeMatch or relatedMatch. Other columns are ignored, so an edited reconciliation worksheet can be uploaded as it is.",
                )
            }}
        </p>
        <p class="help-text">
            {{ $gettext("Up to 10,000 rows and 5 MB.") }}
        </p>
        <FileUpload
            accept=".csv,text/csv"
            mode="basic"
            :auto="false"
            :choose-label="$gettext('Choose File')"
            :multiple="false"
            :disabled="isDisabled"
            :pt="{ input: { id: FILE_INPUT_ID } }"
            @select="onFileSelected"
        />
    </div>
</template>

<style scoped>
.match-link-import-upload {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.match-link-import-upload .help-text {
    margin: 0;
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-text-muted-color);
}
</style>
