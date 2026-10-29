<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Dialog from "primevue/dialog";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import Tag from "primevue/tag";
import MatchLinkImportPreview from "@/arches_lingo/components/generic/MatchLinkImportDialog/components/MatchLinkImportPreview.vue";
import MatchLinkImportUpload from "@/arches_lingo/components/generic/MatchLinkImportDialog/components/MatchLinkImportUpload.vue";

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
    buildOutcomeLabels,
    describeOutcome,
} from "@/arches_lingo/components/generic/MatchLinkImportDialog/utils.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    ERROR,
    INFO,
    SECONDARY,
    SUCCESS,
    WARN,
} from "@/arches_lingo/constants.ts";

import type {
    MatchLinkImportOutcome,
    MatchLinkImportPreview as MatchLinkImportPreviewData,
    MatchLinkImportRecord,
} from "@/arches_lingo/types.ts";

const CLOSE_EVENT = "close" as const;

// Set when opened from a scheme, so only that scheme's concepts receive links.
const { schemeId } = defineProps<{
    schemeId?: string;
}>();

const emit = defineEmits<{
    (event: typeof CLOSE_EVENT): void;
}>();

const { $gettext, $ngettext } = useGettext();
const toast = useToast();
const outcomeLabels = buildOutcomeLabels($gettext);

const isVisible = ref(true);
const selectedFile = ref<File | null>(null);
const preview = ref<MatchLinkImportPreviewData | null>(null);
const previewErrorMessage = ref<string | null>(null);
const isPreviewing = ref(false);
const isApplying = ref(false);
const finishedImport = ref<MatchLinkImportRecord | null>(null);
let isUnmounted = false;

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

const finishedSeverity = computed(() =>
    finishedImport.value?.error_message ? WARN : SUCCESS,
);

const finishedOutcomeTotals = computed(() =>
    (
        Object.entries(finishedImport.value?.outcome_counts ?? {}) as [
            MatchLinkImportOutcome,
            number,
        ][]
    ).map(([outcome, count]) => ({
        outcome,
        text: $gettext("%{label}: %{count}", {
            label: describeOutcome(outcomeLabels, outcome),
            count: String(count),
        }),
    })),
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
            "%{count} row checked",
            "%{count} rows checked",
            preview.value.total_rows,
            { count: String(preview.value.total_rows) },
        );
    }
    return "";
});

onBeforeUnmount(() => {
    isUnmounted = true;
});

async function onFileSelected(file: File | null): Promise<void> {
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
        MATCH_LINK_IMPORT_IN_PROGRESS_STATUSES.includes(currentImport.status)
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

function reportFinishedImport(matchLinkImport: MatchLinkImportRecord): void {
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
        severity: finishedSeverity.value,
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
                @file-selected="onFileSelected"
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

            <Message
                v-if="finishedImport"
                :severity="finishedSeverity"
                :closable="false"
            >
                <div class="finished-summary">
                    <span>{{ $gettext("Import finished.") }}</span>
                    <span v-if="finishedImport.error_message">{{
                        finishedImport.error_message
                    }}</span>
                    <Tag
                        v-for="total in finishedOutcomeTotals"
                        :key="total.outcome"
                        :severity="
                            total.outcome === OUTCOME_ADD ? SUCCESS : SECONDARY
                        "
                        :value="total.text"
                    />
                </div>
            </Message>

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
.dialog-body {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.dialog-body .working {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

/* Screen reader only: the visible spinner and summary say the same thing. */
.dialog-body .status-announcement {
    position: absolute;
    width: 0.0625rem;
    height: 0.0625rem;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
}

.dialog-body .preview-error {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.dialog-body .finished-summary {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
}

.dialog-body .working .spinner {
    width: 2rem;
    height: 2rem;
}

.dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
}
</style>
