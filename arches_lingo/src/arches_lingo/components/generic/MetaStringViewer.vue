<script setup lang="ts">
import { inject, ref } from "vue";
import { useGettext } from "vue3-gettext";

import DataTable from "primevue/datatable";
import Column from "primevue/column";
import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";
import { useConfirm } from "primevue/useconfirm";

import { deleteLingoTile } from "@/arches_lingo/api.ts";
import { SECONDARY } from "@/arches_lingo/constants.ts";
import { DANGER } from "@/arches_lingo/constants.ts";

import type { MetaStringText } from "@/arches_lingo/types.ts";

const props = defineProps<{
    metaStringText: MetaStringText;
    metaStrings?: object[];
    graphSlug: string;
    nodegroupAlias: string;
    componentName: string;
}>();

const { $gettext } = useGettext();
const confirm = useConfirm();

const openEditor =
    inject<(componentName: string, tileid?: string) => void>("openEditor");
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
        openEditor!(props.componentName, undefined);
    } catch (error) {
        console.error(error);
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
                            @click="
                                openEditor!(
                                    componentName,
                                    slotProps.data.tileid,
                                )
                            "
                        />
                        <Button
                            icon="pi pi-trash"
                            :aria-label="$gettext('delete')"
                            severity="danger"
                            outlined
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
    <div v-else>{{ props.metaStringText.noRecords }}</div>
</template>
<style scoped>
:deep(.drawer) {
    padding: 1rem 2rem;
}

.controls {
    display: flex;
    flex-direction: row;
}
.controls button {
    margin: 0 0.5rem;
}
</style>
