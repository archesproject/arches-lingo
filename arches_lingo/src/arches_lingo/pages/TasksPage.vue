<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useGettext } from "vue3-gettext";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Paginator from "primevue/paginator";
import Skeleton from "primevue/skeleton";
import Tag from "primevue/tag";

import { cancelTask, deleteTask, fetchUserTasks } from "@/arches_lingo/api.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    ERROR,
    SUCCESS,
} from "@/arches_lingo/constants.ts";

import type {
    LoadEventTask,
    TaskPaginator,
} from "@/arches_lingo/types/tasks.ts";

const { $gettext } = useGettext();
const confirm = useConfirm();
const toast = useToast();

const isLoading = ref(true);
const tasks = ref<LoadEventTask[]>([]);
const paginator = ref<TaskPaginator>({
    total: 0,
    total_pages: 1,
    current_page: 1,
    has_next: false,
    has_previous: false,
});
const cancellingTaskId = ref<string | null>(null);
const deletingTaskId = ref<string | null>(null);

onMounted(loadTasks);

async function loadTasks(page = 1) {
    isLoading.value = true;
    try {
        const result = await fetchUserTasks(page);
        tasks.value = result.events;
        paginator.value = result.paginator;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to load tasks"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
    }
}

function onPageChange(event: { page: number }) {
    loadTasks(event.page + 1);
}

function formatDateTime(isoString: string | null): string {
    if (!isoString) return "—";
    return new Date(isoString).toLocaleString();
}

function statusSeverity(
    task: LoadEventTask,
): "success" | "danger" | "warn" | "info" | "secondary" | undefined {
    if (task.complete && task.successful) return "success";
    if (task.complete && task.successful === false) return "danger";
    if (task.status === "cancelled") return "warn";
    if (task.status === "failed") return "danger";
    if (!task.complete) return "info";
    return "secondary";
}

function statusLabel(task: LoadEventTask): string {
    if (task.status === "cancelled") return $gettext("Cancelled");
    if (task.complete && task.successful) return $gettext("Complete");
    if (task.complete && task.successful === false) return $gettext("Failed");
    if (!task.complete) return task.status ?? $gettext("Running");
    return task.status ?? $gettext("Unknown");
}

function isTaskCancellable(task: LoadEventTask): boolean {
    return !task.complete && task.status !== "cancelled";
}

function isTaskDeletable(task: LoadEventTask): boolean {
    return (
        task.complete || task.status === "cancelled" || task.status === "failed"
    );
}

async function requestCancelTask(task: LoadEventTask) {
    confirm.require({
        group: "task-confirm",
        message: $gettext("Cancel this task? This cannot be undone."),
        header: $gettext("Cancel Task"),
        icon: "pi pi-exclamation-triangle",
        acceptLabel: $gettext("Yes, cancel task"),
        rejectLabel: $gettext("No"),
        accept: async () => {
            cancellingTaskId.value = task.loadid;
            try {
                const result = await cancelTask(task.loadid);
                if (result.success) {
                    toast.add({
                        severity: SUCCESS,
                        life: DEFAULT_TOAST_LIFE,
                        summary: $gettext("Task cancelled"),
                    });
                    await loadTasks(paginator.value.current_page);
                }
            } catch (error) {
                toast.add({
                    severity: ERROR,
                    life: DEFAULT_ERROR_TOAST_LIFE,
                    summary: $gettext("Unable to cancel task"),
                    detail: error instanceof Error ? error.message : undefined,
                });
            } finally {
                cancellingTaskId.value = null;
            }
        },
    });
}

async function requestDeleteTask(task: LoadEventTask) {
    confirm.require({
        group: "task-confirm",
        message: $gettext(
            "Permanently delete this task record? This cannot be undone.",
        ),
        header: $gettext("Delete Task"),
        icon: "pi pi-exclamation-triangle",
        acceptLabel: $gettext("Yes, delete"),
        rejectLabel: $gettext("No"),
        accept: async () => {
            deletingTaskId.value = task.loadid;
            try {
                await deleteTask(task.loadid);
                toast.add({
                    severity: SUCCESS,
                    life: DEFAULT_TOAST_LIFE,
                    summary: $gettext("Task deleted"),
                });
                await loadTasks(paginator.value.current_page);
            } catch (error) {
                toast.add({
                    severity: ERROR,
                    life: DEFAULT_ERROR_TOAST_LIFE,
                    summary: $gettext("Unable to delete task"),
                    detail: error instanceof Error ? error.message : undefined,
                });
            } finally {
                deletingTaskId.value = null;
            }
        },
    });
}
</script>

<template>
    <div class="tasks-page">
        <div class="tasks-header">
            <h1 class="page-title">
                <i
                    class="pi pi-list"
                    aria-hidden="true"
                />
                {{ $gettext("My Tasks") }}
            </h1>
            <p class="page-subtitle">
                {{
                    $gettext(
                        "Track the status of your import and export operations.",
                    )
                }}
            </p>
        </div>

        <div
            v-if="isLoading"
            class="skeleton-table"
        >
            <Skeleton
                v-for="row in 5"
                :key="row"
                height="3rem"
                class="skeleton-row"
            />
        </div>

        <template v-else>
            <DataTable
                :value="tasks"
                class="tasks-table"
                :empty-message="$gettext('No tasks found.')"
            >
                <Column
                    field="etl_module.name"
                    :header="$gettext('Operation')"
                >
                    <template #body="{ data }">
                        {{ data.etl_module?.name ?? "—" }}
                    </template>
                </Column>

                <Column :header="$gettext('Status')">
                    <template #body="{ data }">
                        <Tag
                            :severity="statusSeverity(data)"
                            :value="statusLabel(data)"
                        />
                    </template>
                </Column>

                <Column :header="$gettext('Started')">
                    <template #body="{ data }">
                        {{ formatDateTime(data.load_start_time) }}
                    </template>
                </Column>

                <Column :header="$gettext('Finished')">
                    <template #body="{ data }">
                        {{ formatDateTime(data.load_end_time) }}
                    </template>
                </Column>

                <Column :header="$gettext('Actions')">
                    <template #body="{ data }">
                        <div class="action-buttons">
                            <Button
                                v-if="isTaskCancellable(data)"
                                icon="pi pi-stop"
                                :label="$gettext('Cancel')"
                                severity="warn"
                                text
                                size="small"
                                :loading="cancellingTaskId === data.loadid"
                                @click="requestCancelTask(data)"
                            />
                            <Button
                                v-if="isTaskDeletable(data)"
                                icon="pi pi-trash"
                                :label="$gettext('Delete')"
                                severity="danger"
                                text
                                size="small"
                                :loading="deletingTaskId === data.loadid"
                                @click="requestDeleteTask(data)"
                            />
                        </div>
                    </template>
                </Column>
            </DataTable>

            <Paginator
                v-if="paginator.total_pages > 1"
                :rows="20"
                :total-records="paginator.total"
                :first="(paginator.current_page - 1) * 20"
                class="tasks-paginator"
                @page="onPageChange"
            />
        </template>
    </div>
</template>

<style scoped>
.tasks-page {
    height: 100%;
    overflow-y: auto;
    padding: 2rem;
    font-family: var(--p-lingo-font-family);
}

.tasks-header {
    margin-bottom: 2rem;
}

.page-title {
    margin: 0;
    font-size: 1.5rem;
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-text-color);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.page-title i {
    font-size: 1.25rem;
}

.page-subtitle {
    margin: 0.25rem 0 0 0;
    font-size: var(--p-lingo-font-size-normal);
    color: var(--p-text-muted-color);
}

.skeleton-table {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.skeleton-row {
    width: 100%;
    border-radius: 0.25rem;
}

.tasks-table {
    border-radius: 0.25rem;
    font-size: var(--p-lingo-font-size-normal);
}

.tasks-paginator {
    margin-top: 1rem;
}

.action-buttons {
    display: flex;
    gap: 0.25rem;
}
</style>
