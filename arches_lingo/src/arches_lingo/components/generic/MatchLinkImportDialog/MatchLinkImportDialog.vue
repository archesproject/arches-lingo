<script setup lang="ts">
import { computed, ref } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Dialog from "primevue/dialog";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import MatchLinkImportPreview from "@/arches_lingo/components/generic/MatchLinkImportDialog/components/MatchLinkImportPreview.vue";
import MatchLinkImportResult from "@/arches_lingo/components/generic/MatchLinkImportDialog/components/MatchLinkImportResult.vue";
import MatchLinkImportUpload from "@/arches_lingo/components/generic/MatchLinkImportDialog/components/MatchLinkImportUpload.vue";

import { useMatchLinkImport } from "@/arches_lingo/components/generic/MatchLinkImportDialog/composables/useMatchLinkImport.ts";
import { OUTCOME_ADD } from "@/arches_lingo/components/generic/MatchLinkImportDialog/utils.ts";
import {
    DEFAULT_TOAST_LIFE,
    ERROR,
    INFO,
    SECONDARY,
} from "@/arches_lingo/constants.ts";

const CLOSE_EVENT = "close" as const;

// Set when opened from a scheme, so only that scheme's concepts receive links.
const { schemeId = undefined } = defineProps<{
    schemeId?: string;
}>();

const emit = defineEmits<{
    (event: typeof CLOSE_EVENT): void;
}>();

const { $gettext, $ngettext } = useGettext();
const toast = useToast();
const {
    preview,
    previewErrorMessage,
    isPreviewing,
    isApplying,
    finishedImport,
    previewFile,
    applyImport,
} = useMatchLinkImport(schemeId);

const isVisible = ref(true);

const linksToAddCount = computed(
    () => preview.value?.counts_by_outcome[OUTCOME_ADD] ?? 0,
);

const canApply = computed(
    () =>
        linksToAddCount.value > 0 &&
        !isPreviewing.value &&
        !isApplying.value &&
        !finishedImport.value,
);

const addLinksLabel = computed(() =>
    $ngettext(
        "Add %{count} link",
        "Add %{count} links",
        linksToAddCount.value,
        {
            count: String(linksToAddCount.value),
        },
    ),
);

const workingText = computed(() => {
    if (isApplying.value) return $gettext("Adding links…");
    if (isPreviewing.value) return $gettext("Checking the file…");
    return "";
});

// Kept in the page from the start, so screen readers announce what changes.
const statusAnnouncement = computed(() => {
    if (workingText.value) return workingText.value;
    if (finishedImport.value) return $gettext("Import finished.");
    if (preview.value) {
        return $ngettext(
            "%{count} link checked",
            "%{count} links checked",
            preview.value.total_links,
            { count: String(preview.value.total_links) },
        );
    }
    return "";
});

function onVisibilityChange(isNowVisible: boolean): void {
    if (!isNowVisible && isApplying.value) {
        toast.add({
            severity: INFO,
            life: DEFAULT_TOAST_LIFE,
            summary: $gettext("The match link import continues"),
            detail: $gettext("You will be notified when it finishes."),
        });
    }
    isVisible.value = isNowVisible;
    if (!isNowVisible) emit(CLOSE_EVENT);
}
</script>

<template>
    <Dialog
        class="match-link-import-dialog"
        position="center"
        :visible="isVisible"
        :modal="true"
        :draggable="false"
        :header="$gettext('Import Match Links')"
        :style="{ width: '60rem', maxWidth: '95vw' }"
        @update:visible="onVisibilityChange"
    >
        <div class="dialog-body">
            <MatchLinkImportUpload
                :is-disabled="isPreviewing || isApplying"
                :is-scheme-scoped="Boolean(schemeId)"
                @file-selected="previewFile"
            />

            <span
                class="status-announcement"
                role="status"
                >{{ statusAnnouncement }}</span
            >

            <div
                v-if="workingText"
                class="working"
                aria-hidden="true"
            >
                <ProgressSpinner class="spinner" />
                <span>{{ workingText }}</span>
            </div>

            <Message
                v-if="previewErrorMessage"
                :severity="ERROR"
                :closable="false"
            >
                <div class="preview-error">
                    <strong>{{
                        $gettext("Unable to read the match links file")
                    }}</strong>
                    <span>{{ previewErrorMessage }}</span>
                </div>
            </Message>

            <MatchLinkImportResult
                v-if="finishedImport"
                :outcome-counts="finishedImport.outcome_counts"
                :error-message="finishedImport.error_message"
            />

            <MatchLinkImportPreview
                v-if="preview && !isPreviewing && !finishedImport"
                :preview="preview"
            />
        </div>

        <template #footer>
            <div class="dialog-footer">
                <Button
                    :label="
                        finishedImport || isApplying
                            ? $gettext('Close')
                            : $gettext('Cancel')
                    "
                    :severity="SECONDARY"
                    @click="onVisibilityChange(false)"
                />
                <Button
                    v-if="!finishedImport"
                    icon="pi pi-link"
                    :label="addLinksLabel"
                    :disabled="!canApply"
                    :loading="isApplying"
                    @click="applyImport"
                />
            </div>
        </template>
    </Dialog>
</template>

<style scoped>
.match-link-import-dialog .dialog-body {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.match-link-import-dialog .dialog-body .working {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

/* Screen reader only: the visible spinner and summary say the same thing. */
.match-link-import-dialog .dialog-body .status-announcement {
    position: absolute;
    width: 0.0625rem;
    height: 0.0625rem;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
}

.match-link-import-dialog .dialog-body .preview-error {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.match-link-import-dialog .dialog-body .working .spinner {
    width: 2rem;
    height: 2rem;
}

.match-link-import-dialog .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
}
</style>
