<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Dialog from "primevue/dialog";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
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
    MATCH_LINK_IMPORT_POLL_INTERVAL_MS,
    OUTCOME_ADD,
    buildOutcomeLabels,
} from "@/arches_lingo/components/generic/MatchLinkImportDialog/utils.ts";
import {
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    ERROR,
    SECONDARY,
    SUCCESS,
} from "@/arches_lingo/constants.ts";

import type {
    MatchLinkImportOutcome,
    MatchLinkImportPreview as MatchLinkImportPreviewData,
    MatchLinkImportRecord,
} from "@/arches_lingo/types.ts";

const CLOSE_EVENT = "close" as const;
const IMPORTED_EVENT = "imported" as const;

const emit = defineEmits<{
    (event: typeof CLOSE_EVENT): void;
    (event: typeof IMPORTED_EVENT): void;
}>();

const { $gettext } = useGettext();
const toast = useToast();
const outcomeLabels = buildOutcomeLabels($gettext);

const isVisible = ref(true);
const selectedFile = ref<File | null>(null);
const preview = ref<MatchLinkImportPreviewData | null>(null);
const isPreviewing = ref(false);
const isApplying = ref(false);
const finishedImport = ref<MatchLinkImportRecord | null>(null);
const isUnmounted = ref(false);

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

const finishedOutcomeSummary = computed(() =>
    (
        Object.entries(finishedImport.value?.outcome_counts ?? {}) as [
            MatchLinkImportOutcome,
            number,
        ][]
    )
        .map(([outcome, count]) => `${outcomeLabels[outcome]}: ${count}`)
        .join(", "),
);

onBeforeUnmount(() => {
    isUnmounted.value = true;
});

async function onFileSelected(file: File | null): Promise<void> {
    selectedFile.value = file;
    preview.value = null;
    finishedImport.value = null;
    if (!file) return;

    isPreviewing.value = true;
    try {
        preview.value = await previewMatchLinkImport(file);
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to read the match links file"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isPreviewing.value = false;
    }
}

async function applyImport(): Promise<void> {
    if (!selectedFile.value) return;
    isApplying.value = true;
    try {
        const startedImport = await startMatchLinkImport(selectedFile.value);
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
    while (
        MATCH_LINK_IMPORT_IN_PROGRESS_STATUSES.includes(currentImport.status)
    ) {
        await new Promise((resolve) =>
            setTimeout(resolve, MATCH_LINK_IMPORT_POLL_INTERVAL_MS),
        );
        if (isUnmounted.value) return null;
        currentImport = await fetchMatchLinkImport(currentImport.id);
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
    toast.add({
        severity: SUCCESS,
        life: DEFAULT_TOAST_LIFE,
        summary: $gettext("%{count} match links added", {
            count: String(matchLinkImport.outcome_counts[OUTCOME_ADD] ?? 0),
        }),
    });
    emit(IMPORTED_EVENT);
}

function onVisibilityChange(isNowVisible: boolean): void {
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
        :closable="!isApplying"
        :header="$gettext('Import match links')"
        :style="{ width: '60rem', maxWidth: '95vw' }"
        @update:visible="onVisibilityChange"
    >
        <div class="dialog-body">
            <MatchLinkImportUpload
                :is-disabled="isPreviewing || isApplying"
                @file-selected="onFileSelected"
            />

            <div
                v-if="isPreviewing || isApplying"
                class="working"
            >
                <ProgressSpinner class="spinner" />
                <span>{{
                    isApplying
                        ? $gettext("Adding links…")
                        : $gettext("Checking the file…")
                }}</span>
            </div>

            <Message
                v-if="finishedImport"
                :severity="SUCCESS"
                :closable="false"
            >
                <span>{{
                    $gettext("Import finished. %{summary}", {
                        summary: finishedOutcomeSummary,
                    })
                }}</span>
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
                        finishedImport ? $gettext('Close') : $gettext('Cancel')
                    "
                    :severity="finishedImport ? SECONDARY : DANGER"
                    :disabled="isApplying"
                    @click="onVisibilityChange(false)"
                />
                <Button
                    v-if="!finishedImport"
                    icon="pi pi-link"
                    :label="
                        $gettext('Add %{count} links', {
                            count: String(linksToAddCount),
                        })
                    "
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
