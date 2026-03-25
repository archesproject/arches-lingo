<script setup lang="ts">
import { computed, inject, ref } from "vue";

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
        return true;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to delete data."),
            detail: error instanceof Error ? error.message : undefined,
        });
        return false;
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
                        @click.stop="
                            () => {
                                rejectCallback();
                                confirm.close();
                            }
                        "
                        @mousedown.stop
                        @mouseup.stop
                    />
                    <Button
                        :label="$gettext('Delete')"
                        :loading="isDeletePending"
                        severity="danger"
                        @click="
                            async () => {
                                const didDelete = await deleteSectionValue(
                                    message.data.tileId,
                                );
                                if (didDelete) {
                                    confirm.close();
                                }
                            }
                        "
                        @mousedown.stop
                        @mouseup.stop
                    />
                </div>
            </div>
        </template>
    </ConfirmDialog>
    <div v-if="props.metaStrings?.length">
        <DataTable
            v-model:expanded-rows="expandedRows"
            class="meta-string-table"
            striped-rows
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
                            class="controls edit-button"
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
                            class="controls delete-button"
                            icon="pi pi-trash"
                            variant="text"
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

.controls {
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    padding: 1.2rem;
    color: var(--p-button-primary-color);
}

.edit-button {
    background: var(--p-button-primary-background);
    border: 0.0625rem solid var(--p-button-primary-active-border-color);
}

.delete-button {
    background: var(--p-button-danger-background);
    border: 0.0625rem solid var(--p-button-danger-border-color);
    color: var(--p-button-danger-color);
}

.button-container .edit-button:hover {
    background: var(--p-button-primary-hover-background);
    border: 0.0625rem solid var(--p-button-primary-hover-border-color);
    color: var(--p-button-primary-hover-color);
}

.button-container .delete-button:hover {
    background: var(--p-button-danger-hover-background);
    border: 0.0625rem solid var(--p-button-danger-hover-border-color);
    color: var(--p-button-danger-hover-color);
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
