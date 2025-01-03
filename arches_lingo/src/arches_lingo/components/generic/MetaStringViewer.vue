<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";
import DataTable from "primevue/datatable";
import Column from "primevue/column";
import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";
import { useConfirm } from "primevue/useconfirm";

import type { MetaString, MetaStringText } from "@/arches_lingo/types.ts";
import { SECONDARY } from "@/arches_lingo/constants.ts";
import { DANGER } from "@/arches_references/constants.ts";

const { $gettext } = useGettext();
const expandedRows = ref([]);
const confirm = useConfirm();

const props = defineProps<{
    metaStringText: MetaStringText;
    metaStrings?: object[];
}>();

const emits = defineEmits(["editString", "deleteString"]);

function confirmDelete(tileId: string) {
    confirm.require({
        header: $gettext("Confirmation"),
        message: props.metaStringText.deleteConfirm,
        group: props.metaStringText.name,
        accept: () => {
            emits("deleteString", tileId);
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
</script>

<template>
    <ConfirmDialog
        :pt="{ root: { style: { fontFamily: 'sans-serif' } } }"
        :group="metaStringText.name"
    />
    <div v-if="props.metaStrings?.length">
        <DataTable
            v-model:expanded-rows="expandedRows"
            :value="props.metaStrings"
        >
            <Column
                expander
                style="width: 3rem"
            />
            <Column
                :header="props.metaStringText.name"
                sortable
            >
                <template #body="slotProps">
                    <slot
                        name="name"
                        :row-data="slotProps.data"
                    />
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
                    />
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
                    />
                </template>
            </Column>
            <Column>
                <template #body="slotProps">
                    <div class="controls">
                        <Button
                            icon="pi pi-file-edit"
                            :aria-label="$gettext('edit')"
                            @click="
                                () =>
                                    emits(
                                        'editString',
                                        (slotProps.data as MetaString).tileid,
                                    )
                            "
                        />
                        <Button
                            icon="pi pi-trash"
                            :aria-label="$gettext('delete')"
                            severity="danger"
                            outlined
                            @click="
                                () =>
                                    confirmDelete(
                                        (slotProps.data as MetaString).tileid,
                                    )
                            "
                        />
                    </div>
                </template>
            </Column>
            <template #expansion="slotProps">
                <div class="drawer">
                    <slot
                        name="drawer"
                        :row-data="slotProps.data"
                    />
                </div>
            </template>
        </DataTable>
    </div>
    <div v-else>{{ props.metaStringText.noRecords }}</div>
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
