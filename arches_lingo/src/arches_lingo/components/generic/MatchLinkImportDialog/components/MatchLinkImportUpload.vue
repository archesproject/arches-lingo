<script setup lang="ts">
import { useId } from "vue";

import { useGettext } from "vue3-gettext";

import FileUpload from "primevue/fileupload";

const FILE_SELECTED_EVENT = "file-selected" as const;

const { isDisabled, isSchemeScoped } = defineProps<{
    isDisabled: boolean;
    isSchemeScoped: boolean;
}>();

const emit = defineEmits<{
    (event: typeof FILE_SELECTED_EVENT, file: File | null): void;
}>();

const { $gettext } = useGettext();

const fileLabelId = useId();
const chooseButtonId = useId();
const helpTextId = useId();

function onFileSelected(event: { files: File[] }): void {
    emit(FILE_SELECTED_EVENT, event.files?.[0] ?? null);
}
</script>

<template>
    <div class="match-link-import-upload">
        <span :id="fileLabelId">{{ $gettext("Match links file (CSV)") }}</span>
        <div
            :id="helpTextId"
            class="help"
        >
            <p class="help-text">
                {{
                    $gettext(
                        "Needs concept_id and match_uri columns. An optional match_type column can be exactMatch (the default), closeMatch or relatedMatch. Other columns are ignored.",
                    )
                }}
            </p>
            <p class="help-text">
                {{
                    $gettext(
                        "A reconciliation worksheet can be uploaded as it is once its match_uri column is filled in, for example in OpenRefine from the reconciled column's matched entity URI. Rows left without a match_uri are skipped. Separate several URIs in one cell with |.",
                    )
                }}
            </p>
            <p class="help-text">
                {{
                    $gettext(
                        "A worksheet value that begins with =, + or @ is exported with a leading apostrophe, so that a spreadsheet does not run it as a formula. Remove the apostrophe in OpenRefine before reconciling that column.",
                    )
                }}
            </p>
            <p
                v-if="isSchemeScoped"
                class="help-text"
            >
                {{ $gettext("Only concepts in this scheme receive links.") }}
            </p>
        </div>
        <!-- PrimeVue hides the file input itself, so the choose button is what
             takes focus and needs the field's name. -->
        <FileUpload
            accept=".csv,text/csv"
            mode="basic"
            :auto="false"
            :choose-label="$gettext('Choose File')"
            :choose-button-props="{
                id: chooseButtonId,
                'aria-labelledby': `${fileLabelId} ${chooseButtonId}`,
                'aria-describedby': helpTextId,
            }"
            :multiple="false"
            :disabled="isDisabled"
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

.match-link-import-upload .help {
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
