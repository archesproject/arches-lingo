<script setup lang="ts">
import { inject } from "vue";
import { useGettext } from "vue3-gettext";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";

import { deleteLingoTile } from "@/arches_lingo/api.ts";
import type { Ref } from "vue";
import type {
    SearchResultItem,
    SearchResultHierarchy,
} from "@/arches_lingo/types.ts";
import {
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    SECONDARY,
    selectedLanguageKey,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";
import { getItemLabel } from "@/arches_component_lab/utils.ts";
import type { Language } from "@/arches_component_lab/types";

const props = defineProps<{
    data: SearchResultHierarchy[];
    componentName: string;
    sectionTitle: string;
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId: string | undefined;
    schemeId?: string;
}>();
const { $gettext } = useGettext();
const confirm = useConfirm();
const toast = useToast();

const selectedLanguage = inject(selectedLanguageKey) as Ref<Language>;
const systemLanguage = inject(systemLanguageKey) as Language;

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
    return item.id === props.schemeId ? "pi pi-folder" : "pi pi-tag";
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
    <div class="viewer-section">
        <ConfirmDialog
            :pt="{ root: { style: { fontFamily: 'sans-serif' } } }"
            group="delete-parent"
        ></ConfirmDialog>

        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>

            <Button
                class="add-button"
                style="min-width: 15rem"
                :label="$gettext('Add Hierarchical Parent')"
                @click="openEditor!(props.componentName)"
            ></Button>
        </div>

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
                            'margin-inline-start': subindex + 'rem',
                            'margin-inline-end': '0.5rem',
                        }"
                    ></span>
                    <span>
                        {{
                            getItemLabel(
                                item,
                                selectedLanguage.code,
                                systemLanguage.code,
                            ).value
                        }}
                    </span>
                    <span
                        v-if="subindex === hierarchy.searchResults.length - 1"
                        class="current-position"
                    >
                        <Button
                            icon="pi pi-file-edit"
                            variant="text"
                            :aria-label="$gettext('edit')"
                            :disabled="hierarchy.isTopConcept"
                            size="small"
                            @click="
                                openEditor!(componentName, hierarchy.tileid)
                            "
                        />
                        <Button
                            v-if="hierarchy.tileid"
                            icon="pi pi-trash"
                            variant="text"
                            :aria-label="$gettext('delete')"
                            severity="danger"
                            size="small"
                            @click="confirmDelete(hierarchy)"
                        />
                    </span>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.section-item {
    padding: var(--p-tree-node-padding);
}
.section-item .current-position button {
    width: 2rem;
    margin-inline-start: 0.5rem;
}
</style>
