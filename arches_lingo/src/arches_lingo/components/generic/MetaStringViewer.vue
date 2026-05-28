<script setup lang="ts">
import { computed, inject, onMounted, onUnmounted, ref } from "vue";

import { useConfirm } from "primevue/useconfirm";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import DataTable from "primevue/datatable";
import Column from "primevue/column";
import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";

import { deleteLingoTile } from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

import type { MetaStringText } from "@/arches_lingo/types.ts";

const props = defineProps<{
    metaStringText: MetaStringText;
    metaStrings?: object[];
    graphSlug: string;
    nodegroupAlias: string;
    componentName: string;
}>();

const toast = useToast();
const { $gettext } = useGettext();
const confirm = useConfirm();

const openEditor =
    inject<(componentName: string, tileId?: string) => void>("openEditor");
const updateAfterComponentDeletion = inject<
    (componentName: string, tileId: string) => void
>("updateAfterComponentDeletion");
const refreshReportSection = inject<(componentName: string) => void>(
    "refreshReportSection",
);
const refreshSchemeHierarchy = inject<() => void>("refreshSchemeHierarchy");
const { isEditor } = useUserStore();

const resourceInstanceLifecycleState = inject<{
    value:
        | {
              can_edit_resource_instances: boolean;
              can_delete_resource_instances: boolean;
          }
        | undefined;
}>("resourceInstanceLifecycleState");

const canEditResourceInstances = computed(() => {
    return Boolean(
        resourceInstanceLifecycleState?.value?.can_edit_resource_instances,
    );
});

const expandedRows = ref([]);
const isDeletePending = ref(false);
const tableContainerRef = ref<HTMLElement | null>(null);
const isScrolledToBottom = ref(true);

let scrollableTableBody: HTMLElement | null = null;

function updateScrollShadow() {
    if (!scrollableTableBody) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollableTableBody;
    isScrolledToBottom.value = scrollTop + clientHeight >= scrollHeight - 1;
}

onMounted(() => {
    scrollableTableBody =
        tableContainerRef.value?.querySelector<HTMLElement>(
            ".p-datatable-table-container",
        ) ?? null;
    if (scrollableTableBody) {
        scrollableTableBody.addEventListener("scroll", updateScrollShadow, {
            passive: true,
        });
        updateScrollShadow();
    }
});

onUnmounted(() => {
    if (scrollableTableBody) {
        scrollableTableBody.removeEventListener("scroll", updateScrollShadow);
    }
});

function confirmDelete(tileId: string) {
    confirm.require({
        header: $gettext("Confirmation"),
        message: props.metaStringText.deleteConfirm,
        group: props.metaStringText.name,
        data: { tileId },
    } as object);
}

async function deleteSectionValue(tileId: string) {
    try {
        isDeletePending.value = true;

        await deleteLingoTile(props.graphSlug, props.nodegroupAlias, tileId);

        refreshReportSection!(props.componentName);
        updateAfterComponentDeletion!(props.componentName, tileId);
        refreshSchemeHierarchy!();

        confirm.close();
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to delete data."),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isDeletePending.value = false;
    }
}
</script>

<template>
    <ConfirmDialog
        :pt="{ root: { style: { fontFamily: 'sans-serif' } } }"
        :group="metaStringText.name"
    >
        <template #container="{ message, rejectCallback }">
            <div
                class="confirm-dialog-content"
                @click.stop
                @mousedown.stop
                @mouseup.stop
            >
                <div class="confirm-dialog-header">
                    {{ message.header }}
                </div>
                <div class="confirm-dialog-message">
                    {{ message.message }}
                </div>
                <div class="confirm-dialog-actions">
                    <Button
                        :label="$gettext('Cancel')"
                        :disabled="isDeletePending"
                        severity="secondary"
                        outlined
                        @click="
                            () => {
                                rejectCallback();
                                confirm.close();
                            }
                        "
                    />
                    <Button
                        :label="$gettext('Delete')"
                        :loading="isDeletePending"
                        severity="danger"
                        @click="() => deleteSectionValue(message.data.tileId)"
                    />
                </div>
            </div>
        </template>
    </ConfirmDialog>
    <div
        v-if="props.metaStrings?.length"
        ref="tableContainerRef"
        class="meta-string-table-container"
        :class="{ 'is-scrolled-to-bottom': isScrolledToBottom }"
    >
        <DataTable
            v-model:expanded-rows="expandedRows"
            class="meta-string-table"
            striped-rows
            scrollable
            scroll-height="38rem"
            table-style="min-width: 100%"
            :value="props.metaStrings"
        >
            <Column
                expander
                style="width: 3rem"
            />
            <Column
                :header="props.metaStringText.name"
                :field="props.metaStringText.sortFields?.name"
                :sortable="Boolean(props.metaStringText.sortFields?.name)"
            >
                <template #body="slotProps">
                    <slot
                        name="name"
                        :row-data="slotProps.data"
                    ></slot>
                </template>
            </Column>
            <Column
                :header="props.metaStringText.type"
                :field="props.metaStringText.sortFields?.type"
                :sortable="Boolean(props.metaStringText.sortFields?.type)"
            >
                <template #body="slotProps">
                    <slot
                        name="type"
                        :row-data="slotProps.data"
                    ></slot>
                </template>
            </Column>
            <Column
                v-if="props.metaStringText?.language"
                :header="props.metaStringText.language"
                :field="props.metaStringText.sortFields?.language"
                :sortable="Boolean(props.metaStringText.sortFields?.language)"
            >
                <template #body="slotProps">
                    <slot
                        name="language"
                        :row-data="slotProps.data"
                    ></slot>
                </template>
            </Column>
            <Column
                v-if="isEditor"
                body-class="action-column"
                header-class="action-column"
                header-style="width: 1%;"
            >
                <template #body="slotProps">
                    <div class="button-container">
                        <Button
                            v-if="canEditResourceInstances"
                            icon="pi pi-file-edit"
                            variant="text"
                            :aria-label="$gettext('edit')"
                            @click="
                                openEditor!(
                                    componentName,
                                    slotProps.data.tileid,
                                )
                            "
                        />
                        <Button
                            v-if="canEditResourceInstances"
                            icon="pi pi-trash"
                            variant="text"
                            severity="danger"
                            :aria-label="$gettext('delete')"
                            @click="confirmDelete(slotProps.data.tileid)"
                        />
                    </div>
                </template>
            </Column>

            <template #expansion="slotProps">
                <div class="drawer">
                    <slot
                        name="drawer"
                        :row-data="slotProps.data"
                    ></slot>
                </div>
            </template>
        </DataTable>
    </div>
    <div
        v-else
        class="no-data"
    >
        {{ props.metaStringText.noRecords }}
    </div>
</template>

<style scoped>
:deep(.drawer) {
    padding: 1rem 2rem;
}

.button-container {
    display: flex;
    gap: 0.25rem;
    justify-content: flex-end;
    width: 100%;
}

.no-data {
    padding: 0.5rem 0;
    margin: 0;
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-light);
    color: var(--p-inputtext-placeholder-color);
}

:deep(.p-dialog) {
    border-radius: 0.125rem;
}

:deep(.p-datatable-tbody > tr > td) {
    color: var(--p-inputtext-placeholder-color);
    font-size: var(--p-lingo-font-size-smallnormal);
    padding: 0.5rem 1rem;
}

:deep(.p-datatable-column-title) {
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-400);
}

:deep(.p-datatable-row-expansion td) {
    padding: 0.5rem 0rem;
}

:deep(.meta-string-table .action-column) {
    text-align: right;
    white-space: nowrap;
}

.meta-string-table-container {
    overflow: hidden;
    position: relative;
}

.meta-string-table-container::after {
    content: "";
    position: absolute;
    inset-block-end: 0;
    inset-inline: 0;
    height: 3rem;
    pointer-events: none;
    background: linear-gradient(to bottom, transparent, rgba(0, 0, 0, 0.07));
    border-radius: 0 0 0.25rem 0.25rem;
    transition: opacity 0.15s ease;
    z-index: 1;
}

.meta-string-table-container.is-scrolled-to-bottom::after {
    opacity: 0;
}

.confirm-dialog-content {
    background: var(--p-dialog-background);
    border-radius: 0.125rem;
    color: var(--p-text-color);
    display: flex;
    flex-direction: column;
    gap: 1rem;
    min-width: 24rem;
    padding: 1.5rem;
}

.confirm-dialog-header {
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
}

.confirm-dialog-message {
    color: var(--p-inputtext-placeholder-color);
    font-size: var(--p-lingo-font-size-smallnormal);
    line-height: 1.5;
}

.confirm-dialog-actions {
    display: flex;
    gap: 0.75rem;
    justify-content: flex-end;
}
</style>
