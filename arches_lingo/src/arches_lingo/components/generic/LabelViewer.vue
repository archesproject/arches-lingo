<script setup lang="ts">
import { ref } from "vue";
import DataTable from "primevue/datatable";
import Column from "primevue/column";
import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";
import { useConfirm } from "primevue/useconfirm";

import type { AppellativeStatus } from "@/arches_lingo/types";
import ControlledListItemViewer from "@/arches_lingo/components/generic/ControlledListItemViewer.vue";
import ResourceInstanceRelationshipsViewer from "@/arches_lingo/components/generic/ResourceInstanceRelationshipsViewer.vue";

const expandedRows = ref([]);
const confirm = useConfirm();

const props = defineProps<{
    value?: AppellativeStatus[];
}>();

const emits = defineEmits(["editLabel", "deleteLabel"]);

function confirmDelete(tileId: string) {
    confirm.require({
        header: "Confirmation",
        message: "Are you sure you want to delete this label?",
        accept: () => {
            emits("deleteLabel", tileId);
        },
        rejectProps: {
            label: "Cancel",
            severity: "secondary",
            outlined: true,
        },
        acceptProps: {
            label: "Delete",
            severity: "danger",
        },
    });
}
</script>
<template>
    <ConfirmDialog
        :pt="{ root: { style: { fontFamily: 'sans-serif' } } }"
    ></ConfirmDialog>
    <DataTable
        v-model:expanded-rows="expandedRows"
        :value="props.value"
        onrowexp
        table-style="min-width: 50rem"
    >
        <Column
            expander
            style="width: 3rem"
        />
        <Column
            field="appellative_status_ascribed_name_content"
            header="Label"
            sortable
        >
            <template #body="slotProps">
                {{
                    (slotProps.data as AppellativeStatus)
                        .appellative_status_ascribed_name_content
                }}
            </template>
        </Column>
        <Column
            field="appellative_status_ascribed_relation"
            header="Label Type"
            sortable
        >
            <template #body="slotProps">
                <ControlledListItemViewer
                    :value="
                        (slotProps.data as AppellativeStatus)
                            .appellative_status_ascribed_relation
                    "
                >
                </ControlledListItemViewer>
            </template>
        </Column>
        <Column
            field="appellative_status_ascribed_name_language"
            header="Label Language"
            sortable
        >
            <template #body="slotProps">
                <ControlledListItemViewer
                    :value="
                        (slotProps.data as AppellativeStatus)
                            .appellative_status_ascribed_name_language
                    "
                >
                </ControlledListItemViewer>
            </template>
        </Column>
        <Column>
            <template #body="slotProps">
                <div class="controls">
                    <Button
                        icon="pi pi-file-edit"
                        aria-label="edit"
                        @click="
                            () =>
                                emits(
                                    'editLabel',
                                    (slotProps.data as AppellativeStatus)
                                        .tileid,
                                )
                        "
                    />
                    <Button
                        icon="pi pi-trash"
                        aria-label="delete"
                        severity="danger"
                        outlined
                        @click="
                            () =>
                                confirmDelete(
                                    (slotProps.data as AppellativeStatus)
                                        .tileid,
                                )
                        "
                    />
                </div>
            </template>
        </Column>
        <template #expansion="slotProps">
            <div class="drawer">
                <div>
                    Bibliographic Sources:
                    <ResourceInstanceRelationshipsViewer
                        :value="
                            (slotProps.data as AppellativeStatus)
                                .appellative_status_data_assignment_object_used
                        "
                    ></ResourceInstanceRelationshipsViewer>
                </div>
                <div>
                    Contributors:
                    <ResourceInstanceRelationshipsViewer
                        :value="
                            (slotProps.data as AppellativeStatus)
                                .appellative_status_data_assignment_actor
                        "
                    ></ResourceInstanceRelationshipsViewer>
                </div>
            </div>
        </template>
    </DataTable>
</template>
<style scoped>
.controls {
    display: flex;
    flex-direction: row;
}
.controls button {
    margin: 0 0.5rem;
}
</style>
