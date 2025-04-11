<script setup lang="ts">
import { inject } from "vue";
import { useGettext } from "vue3-gettext";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";

import { deleteLingoTile, upsertLingoTile } from "@/arches_lingo/api.ts";
import type { SearchResultItem, SearchResultHierarchy } from "@/arches_lingo/types.ts";
import {
    ENGLISH,
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    SECONDARY,
} from "@/arches_lingo/constants.ts";
import { getItemLabel } from "@/arches_vue_utils/utils.ts";

const props = defineProps<{
    data: SearchResultHierarchy[];
    componentName: string;
    sectionTitle: string;
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId: string | undefined;
    scheme?: string;
}>();
const { $gettext } = useGettext();
const confirm = useConfirm();
const toast = useToast();

const openEditor =
    inject<(componentName: string, tileId?: string) => void>("openEditor");

const updateAfterComponentDeletion = inject<
    (componentName: string, tileId: string) => void
>("updateAfterComponentDeletion");

const refreshReportSection = inject<(componentName: string) => void>(
    "refreshReportSection",
);

function getIcon(item: SearchResultItem) {
    //TODO need a better way to determine if item is a scheme or not
    return item.id === props.scheme ? "pi pi-folder" : "pi pi-tag";
}

function confirmDelete(tileId: string) {
    confirm.require({
        header: $gettext("Confirmation"),
        message: $gettext("Are you sure you want to delete the parent relationship? "+tileId),
        group: "delete-parent",
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
        await upsertLingoTile(
            props.graphSlug,
            props.nodegroupAlias,
            {
                resourceinstance: props.resourceInstanceId,
                aliased_data: { top_concept_of: props.scheme },
                tileid: undefined,
            },
        );

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
    <div class="section-header">
        <h2>{{ props.sectionTitle }}</h2>

        <Button
            :label="$gettext('Add to New Parent Concept')"
            @click="openEditor!(props.componentName)"
        ></Button>
    </div>
    <ConfirmDialog
        :pt="{ root: { style: { fontFamily: 'sans-serif' } } }"
        group="delete-parent"
    ></ConfirmDialog>
    <div>
        <div
            v-for="(searchResults, index) in props.data"
            :key="index"
        >
            <div>
                <span>{{ $gettext("Lineage " + (index + 1)) }}</span>
            </div>
            <div
                v-for="(item, index) in searchResults"
                :key="item.id"
                class="section-item"
            >
                <span
                    :class="getIcon(item)"
                    :style="{
                        'margin-left': index + 'rem',
                        'margin-right': '0.5rem',
                    }"
                ></span>
                <span>
                    {{ getItemLabel(item, ENGLISH.code, ENGLISH.code).value }}
                </span>
                <span v-if="index === searchResults.length - 1">
                    <Button
                        icon="pi pi-file-edit"
                        :aria-label="$gettext('edit')"
                        size="small"
                        style="width: 2rem"
                        @click="
                            openEditor!(
                                componentName,
                                searchResults.tileid,
                            )
                        "
                    />
                    <Button
                        icon="pi pi-trash"
                        :aria-label="$gettext('delete')"
                        severity="danger"
                        size="small"
                        style="width: 2rem"
                        outlined
                        @click="confirmDelete(searchResults.tileid)"
                    />
                </span>
            </div>
        </div>
    </div>
</template>

<style scoped>
.section-item {
    padding: var(--p-tree-node-padding);
}
.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 0.125rem solid var(--p-menubar-border-color);
}
</style>
