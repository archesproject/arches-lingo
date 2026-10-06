<script setup lang="ts">
import { computed, ref } from "vue";

import { storeToRefs } from "pinia";
import { useGettext } from "vue3-gettext";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";

import {
    deleteConceptMatchRun,
    linkConceptMatchCandidates,
    updateAllConceptMatchCandidates,
    updateConceptMatchCandidates,
} from "@/arches_lingo/api.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { useErrorToast } from "@/arches_lingo/components/ConceptMatching/composables/useErrorToast.ts";
import {
    CANDIDATE_STATUS_DISMISSED,
    CANDIDATE_STATUS_PENDING,
} from "@/arches_lingo/components/ConceptMatching/constants.ts";
import { describeSkippedReasons } from "@/arches_lingo/components/ConceptMatching/utils.ts";
import {
    DANGER,
    DEFAULT_TOAST_LIFE,
    SECONDARY,
    SUCCESS,
    WARN,
} from "@/arches_lingo/constants.ts";

import type {
    ConceptMatchCandidateStatus,
    ConceptMatchLinkResult,
    ConceptMatchStatusChange,
} from "@/arches_lingo/types.ts";

const CHANGE_ALL_CONFIRM_GROUP = "change-all-matches";
const DELETE_RUN_CONFIRM_GROUP = "delete-match-run";

const ACTION_LINK = "link" as const;
const ACTION_UPDATE_SELECTION = "update-selection" as const;
const ACTION_CHANGE_ALL = "change-all" as const;
const ACTION_DELETE_RUN = "delete-run" as const;

type ReviewAction =
    | typeof ACTION_LINK
    | typeof ACTION_UPDATE_SELECTION
    | typeof ACTION_CHANGE_ALL
    | typeof ACTION_DELETE_RUN;

const {
    runId,
    candidateStatus,
    selectedCandidateIds,
    pendingCount,
    dismissedCount,
    candidateCount,
    isRunUnfinished,
    canDeleteRun,
} = defineProps<{
    runId: number;
    candidateStatus: ConceptMatchCandidateStatus;
    selectedCandidateIds: number[];
    pendingCount: number;
    dismissedCount: number;
    candidateCount: number;
    isRunUnfinished: boolean;
    canDeleteRun: boolean;
}>();

const emit = defineEmits<{
    (event: "review-changed"): void;
    (event: "run-deleted", payload: { wasCancelled: boolean }): void;
}>();

const { $gettext, $ngettext } = useGettext();
const toast = useToast();
const confirm = useConfirm();
const { selectedLanguage } = storeToRefs(useLanguageStore());
const { reportError } = useErrorToast();

const actionInFlight = ref<ReviewAction | null>(null);

const isActionInFlight = computed(() => actionInFlight.value !== null);

const isReviewingPending = computed(
    () => candidateStatus === CANDIDATE_STATUS_PENDING,
);
const isReviewingDismissed = computed(
    () => candidateStatus === CANDIDATE_STATUS_DISMISSED,
);
const selectedCount = computed(() => selectedCandidateIds.length);
const canActOnSelection = computed(
    () => selectedCount.value > 0 && !isActionInFlight.value,
);
const canDismissAll = computed(
    () => isReviewingPending.value && pendingCount > 0,
);
const canRestoreAll = computed(
    () => isReviewingDismissed.value && dismissedCount > 0,
);

function describeSkippedDetail(
    skipped: Record<string, number>,
): string | undefined {
    if (!Object.keys(skipped).length) return undefined;
    const reasonLabels: Record<string, string> = {
        missing_uri: $gettext("no URI to point at"),
        not_editable: $gettext("neither concept can be edited"),
        missing_concept: $gettext("concept no longer exists"),
        already_decided: $gettext("already dismissed, linked or merged"),
    };
    return $gettext("Skipped: %{reasons}.", {
        reasons: describeSkippedReasons(
            skipped,
            (reason, count) =>
                $gettext("%{count} (%{reason})", {
                    count: String(count),
                    reason: reasonLabels[reason] ?? reason,
                }),
            selectedLanguage.value.code,
        ),
    });
}

function reportStatusChange(result: ConceptMatchStatusChange): void {
    toast.add({
        severity: result.updated ? SUCCESS : WARN,
        life: DEFAULT_TOAST_LIFE,
        summary:
            result.status === CANDIDATE_STATUS_DISMISSED
                ? $ngettext(
                      "Dismissed %{count} pair",
                      "Dismissed %{count} pairs",
                      result.updated,
                      { count: String(result.updated) },
                  )
                : $ngettext(
                      "Returned %{count} pair to the queue",
                      "Returned %{count} pairs to the queue",
                      result.updated,
                      { count: String(result.updated) },
                  ),
        detail: describeSkippedDetail(result.skipped),
    });
}

function reportLinkResult(result: ConceptMatchLinkResult): void {
    const oneWayDetail = result.linked_one_way
        ? $ngettext(
              "%{count} recorded on one side only, because the other concept cannot be edited.",
              "%{count} recorded on one side only, because the other concepts cannot be edited.",
              result.linked_one_way,
              { count: String(result.linked_one_way) },
          )
        : undefined;
    const skippedDetail = describeSkippedDetail(result.skipped);

    toast.add({
        severity: result.linked ? SUCCESS : WARN,
        life: DEFAULT_TOAST_LIFE,
        summary: $ngettext(
            "Linked %{count} pair",
            "Linked %{count} pairs",
            result.linked,
            { count: String(result.linked) },
        ),
        detail:
            oneWayDetail && skippedDetail
                ? $gettext("%{oneWay} %{skipped}", {
                      oneWay: oneWayDetail,
                      skipped: skippedDetail,
                  })
                : oneWayDetail ?? skippedDetail,
    });
}

async function runExclusively(
    action: ReviewAction,
    request: () => Promise<void>,
): Promise<void> {
    if (isActionInFlight.value) return;
    actionInFlight.value = action;
    try {
        await request();
    } finally {
        actionInFlight.value = null;
    }
}

async function linkSelection(): Promise<void> {
    await runExclusively(ACTION_LINK, async function () {
        try {
            reportLinkResult(
                await linkConceptMatchCandidates(runId, selectedCandidateIds),
            );
            emit("review-changed");
        } catch (error) {
            reportError(error, $gettext("Could not link the selected pairs."));
        }
    });
}

async function setStatusForSelection(
    status: ConceptMatchCandidateStatus,
): Promise<void> {
    await runExclusively(ACTION_UPDATE_SELECTION, async function () {
        try {
            reportStatusChange(
                await updateConceptMatchCandidates(
                    runId,
                    selectedCandidateIds,
                    status,
                ),
            );
            emit("review-changed");
        } catch (error) {
            reportError(
                error,
                $gettext("Could not update the selected pairs."),
            );
        }
    });
}

function confirmStatusChangeForAll(status: ConceptMatchCandidateStatus): void {
    const isDismissing = status === CANDIDATE_STATUS_DISMISSED;
    const affectedCount = isDismissing ? pendingCount : dismissedCount;

    confirm.require({
        group: CHANGE_ALL_CONFIRM_GROUP,
        header: isDismissing
            ? $gettext("Dismiss everything left?")
            : $gettext("Restore everything dismissed?"),
        message: isDismissing
            ? $ngettext(
                  "The %{count} pair still awaiting a decision will be dismissed, in this run and in every other search that finds it. It can be restored from the dismissed list.",
                  "All %{count} pairs still awaiting a decision will be dismissed, in this run and in every other search that finds them. They can be restored from the dismissed list.",
                  affectedCount,
                  { count: String(affectedCount) },
              )
            : $ngettext(
                  "The %{count} dismissed pair will be returned to the queue, unless it has been linked or merged since.",
                  "All %{count} dismissed pairs will be returned to the queue, except any linked or merged since.",
                  affectedCount,
                  { count: String(affectedCount) },
              ),
        accept: () => changeStatusForAll(status),
    });
}

async function changeStatusForAll(
    status: ConceptMatchCandidateStatus,
): Promise<void> {
    await runExclusively(ACTION_CHANGE_ALL, async function () {
        try {
            reportStatusChange(
                await updateAllConceptMatchCandidates(runId, status),
            );
            emit("review-changed");
        } catch (error) {
            reportError(
                error,
                status === CANDIDATE_STATUS_DISMISSED
                    ? $gettext("Could not dismiss the remaining pairs.")
                    : $gettext("Could not restore the dismissed pairs."),
            );
        }
    });
}

function confirmDeleteRun(): void {
    const wasCancelled = isRunUnfinished;
    confirm.require({
        group: DELETE_RUN_CONFIRM_GROUP,
        header: wasCancelled
            ? $gettext("Cancel this run?")
            : $gettext("Delete this run?"),
        message: wasCancelled
            ? $gettext(
                  "The search stops, and the run and everything it has found so far are deleted. This cannot be undone.",
              )
            : $ngettext(
                  "The run and its %{count} pair are deleted. Pairs already dismissed, linked or merged stay that way. This cannot be undone.",
                  "The run and all %{count} of its pairs are deleted. Pairs already dismissed, linked or merged stay that way. This cannot be undone.",
                  candidateCount,
                  { count: String(candidateCount) },
              ),
        accept: () => deleteRun(wasCancelled),
    });
}

async function deleteRun(wasCancelled: boolean): Promise<void> {
    await runExclusively(ACTION_DELETE_RUN, async function () {
        try {
            await deleteConceptMatchRun(runId);
            toast.add({
                severity: SUCCESS,
                life: DEFAULT_TOAST_LIFE,
                summary: wasCancelled
                    ? $gettext("Run cancelled")
                    : $gettext("Run deleted"),
            });
            emit("run-deleted", { wasCancelled });
        } catch (error) {
            reportError(
                error,
                wasCancelled
                    ? $gettext("Could not cancel the run.")
                    : $gettext("Could not delete the run."),
            );
        }
    });
}
</script>

<template>
    <div class="review-actions">
        <template v-if="isReviewingPending">
            <Button
                class="action-button"
                icon="pi pi-link"
                :label="
                    $gettext('Link %{count}', { count: String(selectedCount) })
                "
                :disabled="!canActOnSelection"
                :loading="actionInFlight === ACTION_LINK"
                @click="linkSelection"
            />
            <Button
                class="action-button"
                icon="pi pi-times"
                :label="
                    $gettext('Dismiss %{count}', {
                        count: String(selectedCount),
                    })
                "
                :severity="SECONDARY"
                :outlined="true"
                :disabled="!canActOnSelection"
                :loading="actionInFlight === ACTION_UPDATE_SELECTION"
                @click="setStatusForSelection(CANDIDATE_STATUS_DISMISSED)"
            />
        </template>

        <Button
            v-if="isReviewingDismissed"
            class="action-button"
            icon="pi pi-undo"
            :label="
                $gettext('Restore %{count}', { count: String(selectedCount) })
            "
            :severity="SECONDARY"
            :outlined="true"
            :disabled="!canActOnSelection"
            :loading="actionInFlight === ACTION_UPDATE_SELECTION"
            @click="setStatusForSelection(CANDIDATE_STATUS_PENDING)"
        />

        <Button
            v-if="canDismissAll"
            class="action-button"
            icon="pi pi-times-circle"
            :label="
                $gettext('Dismiss all %{count}', {
                    count: String(pendingCount),
                })
            "
            :severity="SECONDARY"
            :outlined="true"
            :disabled="isActionInFlight"
            :loading="actionInFlight === ACTION_CHANGE_ALL"
            @click="confirmStatusChangeForAll(CANDIDATE_STATUS_DISMISSED)"
        />

        <Button
            v-if="canRestoreAll"
            class="action-button"
            icon="pi pi-replay"
            :label="
                $gettext('Restore all %{count}', {
                    count: String(dismissedCount),
                })
            "
            :severity="SECONDARY"
            :outlined="true"
            :disabled="isActionInFlight"
            :loading="actionInFlight === ACTION_CHANGE_ALL"
            @click="confirmStatusChangeForAll(CANDIDATE_STATUS_PENDING)"
        />

        <Button
            v-if="canDeleteRun"
            class="action-button"
            :icon="isRunUnfinished ? 'pi pi-ban' : 'pi pi-trash'"
            :label="
                isRunUnfinished
                    ? $gettext('Cancel run')
                    : $gettext('Delete run')
            "
            :severity="DANGER"
            :outlined="true"
            :disabled="isActionInFlight"
            :loading="actionInFlight === ACTION_DELETE_RUN"
            @click="confirmDeleteRun"
        />

        <ConfirmDialog :group="CHANGE_ALL_CONFIRM_GROUP" />
        <ConfirmDialog :group="DELETE_RUN_CONFIRM_GROUP" />
    </div>
</template>

<style scoped>
.review-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.review-actions .action-button {
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
}
</style>
