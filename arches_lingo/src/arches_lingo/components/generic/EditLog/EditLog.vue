<script setup lang="ts">
import { inject, onMounted, ref } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Dialog from "primevue/dialog";
import Skeleton from "primevue/skeleton";

import {
    fetchResourceEditLog,
    revertResourceToTimestamp,
} from "@/arches_lingo/api.ts";
import {
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    ERROR,
    SUCCESS,
} from "@/arches_lingo/constants.ts";

import type { DataComponentMode, EditLogEntry } from "@/arches_lingo/types.ts";

const props = defineProps<{
    mode: DataComponentMode;
    sectionTitle: string;
    componentName: string;
    graphSlug: string;
    resourceInstanceId: string | undefined;
    nodegroupAlias: string;
}>();

const refreshReportSection = inject<(componentName: string) => void>(
    "refreshReportSection",
);

const toast = useToast();
const { $gettext } = useGettext();

const isLoading = ref(true);
const isReverting = ref(false);
const edits = ref<EditLogEntry[]>([]);
const pendingRevertTimestamp = ref<string | null>(null);
const revertConfirmMessage = ref("");

onMounted(async () => {
    await loadEditLog();
});

async function loadEditLog() {
    if (!props.resourceInstanceId) {
        isLoading.value = false;
        return;
    }
    isLoading.value = true;
    try {
        const data = await fetchResourceEditLog(props.resourceInstanceId);
        edits.value = data.edits;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch edit history"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
    }
}

function formatTimestamp(timestamp: string) {
    return new Date(timestamp).toLocaleString();
}

function formatUser(edit: EditLogEntry) {
    const name = [edit.user_firstname, edit.user_lastname]
        .filter(Boolean)
        .join(" ");
    return name || edit.user_username || edit.user_email || $gettext("Unknown");
}

function getEditTypeIcon(edittype: string) {
    const icons: Record<string, string> = {
        create: "pi-plus-circle",
        bulk_create: "pi-plus-circle",
        delete: "pi-trash",
        "tile create": "pi-plus",
        "tile edit": "pi-pencil",
        "tile delete": "pi-minus-circle",
        update_resource_instance_lifecycle_state: "pi-sync",
    };
    return icons[edittype] ?? "pi-circle";
}

function getEditTypeSeverity(edittype: string) {
    if (edittype === "delete" || edittype === "tile delete") return "danger";
    if (
        edittype === "create" ||
        edittype === "bulk_create" ||
        edittype === "tile create"
    )
        return "success";
    return "info";
}

function formatEditTypeLabel(edit: EditLogEntry): string {
    if (edit.card_name && edit.edittype.startsWith("tile ")) {
        return edit.edittype_label.replace("Tile", edit.card_name);
    }
    return edit.edittype_label;
}

function canRevert(edit: EditLogEntry) {
    return (
        edit.edittype !== "create" &&
        edit.edittype !== "bulk_create" &&
        edit.edittype !== "delete"
    );
}

function confirmRevert(edit: EditLogEntry) {
    revertConfirmMessage.value = $gettext(
        "Are you sure you want to revert to the state at %{timestamp}? All changes made after this point will be undone.",
    ).replace("%{timestamp}", formatTimestamp(edit.timestamp));
    pendingRevertTimestamp.value = edit.timestamp;
}

function cancelRevert() {
    pendingRevertTimestamp.value = null;
    revertConfirmMessage.value = "";
}

async function acceptRevert() {
    if (!pendingRevertTimestamp.value) return;
    const timestamp = pendingRevertTimestamp.value;
    pendingRevertTimestamp.value = null;
    await performRevert(timestamp);
}

async function performRevert(timestamp: string) {
    if (!props.resourceInstanceId) return;
    isReverting.value = true;
    try {
        const result = await revertResourceToTimestamp(
            props.resourceInstanceId,
            timestamp,
        );
        const isSuccess = result.status === "ok";
        toast.add({
            severity: isSuccess ? SUCCESS : "warn",
            life: DEFAULT_TOAST_LIFE,
            summary: isSuccess
                ? $gettext("Resource reverted successfully")
                : $gettext("Resource partially reverted"),
            detail: result.errors?.join("; "),
        });
        // Refresh the edit log and all report sections
        await loadEditLog();
        refreshReportSection?.("all");
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Revert failed"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isReverting.value = false;
    }
}
</script>

<template>
    <Dialog
        :visible="pendingRevertTimestamp !== null"
        :modal="true"
        :header="$gettext('Confirm Revert')"
        :closable="false"
        @update:visible="cancelRevert"
    >
        <p class="revert-dialog-message">{{ revertConfirmMessage }}</p>
        <template #footer>
            <Button
                :label="$gettext('Cancel')"
                severity="secondary"
                outlined
                @click="cancelRevert"
            />
            <Button
                :label="$gettext('Revert')"
                :severity="DANGER"
                :loading="isReverting"
                @click="acceptRevert"
            />
        </template>
    </Dialog>

    <div class="edit-log">
        <div class="edit-log-header">
            <h3>{{ $gettext("Edit History") }}</h3>
        </div>

        <Skeleton
            v-if="isLoading"
            style="width: 100%; height: 16rem"
        />

        <div
            v-else-if="!edits.length"
            class="no-edits"
        >
            <i class="pi pi-history no-edits-icon" />
            <p>{{ $gettext("No edit history found.") }}</p>
        </div>

        <div
            v-else
            class="edit-log-entries"
        >
            <div
                v-for="(edit, index) in edits"
                :key="edit.editlogid"
                class="edit-entry"
            >
                <div class="edit-entry-timeline">
                    <div
                        :class="[
                            'edit-type-dot',
                            `edit-type-${getEditTypeSeverity(edit.edittype)}`,
                        ]"
                    >
                        <i :class="['pi', getEditTypeIcon(edit.edittype)]" />
                    </div>
                    <div
                        v-if="index < edits.length - 1"
                        class="timeline-line"
                    />
                </div>

                <div class="edit-entry-body">
                    <div class="edit-entry-top">
                        <span class="edit-type-label">
                            {{ formatEditTypeLabel(edit) }}
                        </span>
                        <Button
                            v-if="canRevert(edit)"
                            class="revert-button"
                            severity="secondary"
                            size="small"
                            :label="$gettext('Revert to here')"
                            :loading="isReverting"
                            :disabled="isReverting"
                            @click="confirmRevert(edit)"
                        />
                    </div>

                    <div
                        v-if="
                            edit.card_name && !edit.edittype.startsWith('tile ')
                        "
                        class="edit-card-name"
                    >
                        <i class="pi pi-table" />
                        {{ edit.card_name }}
                    </div>

                    <div class="edit-meta">
                        <span class="edit-user">
                            <i class="pi pi-user" />
                            {{ formatUser(edit) }}
                        </span>
                        <span class="edit-timestamp">
                            <i class="pi pi-clock" />
                            {{ formatTimestamp(edit.timestamp) }}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.edit-log {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
}

.edit-log-header {
    padding: 0.75rem 1rem 0.5rem;
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    background: var(--p-header-background);
}

.edit-log-header h3 {
    margin: 0;
    font-size: var(--p-lingo-font-size-medium);
    font-weight: var(--p-lingo-font-weight-normal);
}

.edit-log-entries {
    overflow-y: auto;
    flex: 1;
    padding: 0.75rem 1rem;
}

.no-edits {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem 1rem;
    color: var(--p-inputtext-placeholder-color);
    gap: 0.5rem;
}

.no-edits-icon {
    font-size: 2rem;
}

.edit-entry {
    display: flex;
    gap: 0.75rem;
    margin-bottom: 0;
}

.edit-entry-timeline {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex-shrink: 0;
    width: 1.75rem;
}

.edit-type-dot {
    width: 1.75rem;
    height: 1.75rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    font-size: 0.75rem;
}

.edit-type-dot.edit-type-info {
    background: var(--p-primary-100);
    color: var(--p-primary-600);
    border: 0.0625rem solid var(--p-primary-300);
}

.edit-type-dot.edit-type-success {
    background: var(--p-green-100);
    color: var(--p-green-700);
    border: 0.0625rem solid var(--p-green-300);
}

.edit-type-dot.edit-type-danger {
    background: var(--p-red-100);
    color: var(--p-red-700);
    border: 0.0625rem solid var(--p-red-300);
}

.timeline-line {
    width: 0.125rem;
    flex: 1;
    min-height: 1rem;
    background: var(--p-highlight-focus-background);
    margin: 0.25rem 0;
}

.edit-entry-body {
    flex: 1;
    padding-bottom: 1rem;
    min-width: 0;
}

.edit-entry-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.edit-type-label {
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-content-color);
}

.revert-button {
    font-size: var(--p-lingo-font-size-xsmall);
    border-radius: 0.125rem;
    flex-shrink: 0;
}

.edit-card-name {
    font-size: var(--p-lingo-font-size-xsmall);
    color: var(--p-primary-500);
    margin-top: 0.2rem;
    display: flex;
    align-items: center;
    gap: 0.25rem;
}

.edit-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-top: 0.3rem;
}

.revert-dialog-message {
    margin: 0;
    font-size: var(--p-lingo-font-size-smallnormal);
}

.edit-user,
.edit-timestamp {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: var(--p-lingo-font-size-xsmall);
    color: var(--p-inputtext-placeholder-color);
}
</style>
