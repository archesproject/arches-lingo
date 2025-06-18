<script setup lang="ts">
import { inject, ref } from "vue";

import { useConfirm } from "primevue/useconfirm";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import DataTable from "primevue/datatable";
import Column from "primevue/column";
import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";

import { deleteLingoTile } from "@/arches_lingo/api.ts";
import {
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    SECONDARY,
} from "@/arches_lingo/constants.ts";

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

const expandedRows = ref([]);

function confirmDelete(tileId: string) {
    confirm.require({
        header: $gettext("Confirmation"),
        message: props.metaStringText.deleteConfirm,
        group: props.metaStringText.name,
        accept: () => {
            deleteSectionValue(tileId);
        },
        rejectProps: {
            label: $gettext("Cancel"),
            severity: SECONDARY,
            outlined: true,
        },
        acceptProps: {
            label: $gettext("Delete"),
            severity: DANGER,
        },
    });
}

async function deleteSectionValue(tileId: string) {
    try {
        await deleteLingoTile(props.graphSlug, props.nodegroupAlias, tileId);

        refreshReportSection!(props.componentName);
        updateAfterComponentDeletion!(props.componentName, tileId);
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to delete data."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}
</script>

<template>
    <ConfirmDialog
        :pt="{ root: { style: { fontFamily: 'sans-serif' } } }"
        :group="metaStringText.name"
    ></ConfirmDialog>
    <div v-if="props.metaStrings?.length">
        <DataTable
            v-model:expanded-rows="expandedRows"
            striped-rows
            :value="props.metaStrings"
        >
            <Column
                expander
                style="width: 3rem"
            />
            <Column
                :header="props.metaStringText.name"
                style="max-width: 50rem"
                sortable
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
                sortable
            >
                <template #body="slotProps">
                    <slot
                        name="type"
                        :row-data="slotProps.data"
                    ></slot>
                </template>
            </Column>
            <Column
                :header="props.metaStringText.language"
                sortable
            >
                <template #body="slotProps">
                    <slot
                        name="language"
                        :row-data="slotProps.data"
                    ></slot>
                </template>
            </Column>
            <Column>
                <template #body="slotProps">
                    <div class="controls">
                        <Button
                            icon="pi pi-file-edit"
                            :aria-label="$gettext('edit')"
                            rounded
                            @click="
                                openEditor!(
                                    componentName,
                                    slotProps.data.tileid,
                                )
                            "
                        />
                        <Button
                            icon="pi pi-trash"
                            class="label-delete-button"
                            :aria-label="$gettext('delete')"
                            severity="danger"
                            rounded
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

.controls {
    display: flex;
    flex-direction: row;
    justify-content: end;
}

.controls button {
    margin: 0 0.25rem;
}

.no-data {
    padding: 0.5rem 0;
    margin: 0;
    font-size: var(--p-lingo-font-size-smallnormal);
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
    color: var(--p-neutral-500);
}

:deep(.p-datatable-row-expansion td) {
    padding: 0.5rem 0rem;
}
</style>
