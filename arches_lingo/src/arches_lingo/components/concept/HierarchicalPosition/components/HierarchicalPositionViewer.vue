<script setup lang="ts">
import { inject } from "vue";
import { useGettext } from "vue3-gettext";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";

import { deleteLingoTile } from "@/arches_lingo/api.ts";
import type {
    SearchResultItem,
    SearchResultHierarchy,
} from "@/arches_lingo/types.ts";
import {
    ENGLISH,
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    SECONDARY,
} from "@/arches_lingo/constants.ts";
import { getItemLabel } from "@/arches_component_lab/utils.ts";

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

function confirmDelete(hierarchy: SearchResultHierarchy) {
    if (!hierarchy.tileid) return;
    confirm.require({
        header: $gettext("Confirmation"),
        message: $gettext(
            "Are you sure you want to delete relationship to parent?",
        ),
        group: "delete-parent",
        accept: () => {
            deleteSectionValue(hierarchy);
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

async function deleteSectionValue(hierarchy: SearchResultHierarchy) {
    try {
        if (props.data.length !== 1) {
            if (hierarchy.searchResults.length > 2) {
                await deleteLingoTile(
                    props.graphSlug,
                    props.nodegroupAlias,
                    hierarchy.tileid!,
                );
            } else if (hierarchy.searchResults.length === 2) {
                await deleteLingoTile(
                    props.graphSlug,
                    "top_concept_of",
                    hierarchy.tileid!,
                );
            }
        } else {
            toast.add({
                severity: ERROR,
                life: DEFAULT_ERROR_TOAST_LIFE,
                summary: $gettext("Failed to delete data."),
                detail: $gettext("Cannot delete the last relationship."),
            });
        }
        refreshReportSection!(props.componentName);
        updateAfterComponentDeletion!(props.componentName, hierarchy.tileid!);
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
            v-for="(hierarchy, index) in props.data"
            :key="index"
        >
            <div>
                <span>{{ $gettext("Lineage " + (index + 1)) }}</span>
            </div>
            <div
                v-for="(item, subindex) in hierarchy.searchResults"
                :key="item.id"
                class="section-item"
            >
                <span
                    :class="getIcon(item)"
                    :style="{
                        'margin-left': subindex + 'rem',
                        'margin-right': '0.5rem',
                    }"
                ></span>
                <span>
                    {{ getItemLabel(item, ENGLISH.code, ENGLISH.code).value }}
                </span>
                <span
                    v-if="subindex === hierarchy.searchResults.length - 1"
                    class="current-position"
                >
                    <Button
                        icon="pi pi-file-edit"
                        :aria-label="$gettext('edit')"
                        :disabled="hierarchy.isTopConcept"
                        size="small"
                        @click="openEditor!(componentName, hierarchy.tileid)"
                    />
                    <Button
                        v-if="hierarchy.tileid"
                        icon="pi pi-trash"
                        :aria-label="$gettext('delete')"
                        severity="danger"
                        size="small"
                        outlined
                        @click="confirmDelete(hierarchy)"
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

.section-item .current-position button {
    width: 2rem;
    margin-left: 0.5rem;
}
</style>
