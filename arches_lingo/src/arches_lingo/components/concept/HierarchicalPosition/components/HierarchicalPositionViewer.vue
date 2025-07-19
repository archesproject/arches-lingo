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
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
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

const refreshSchemeHierarchy = inject<() => void>("refreshSchemeHierarchy");

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

            refreshSchemeHierarchy!();
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
    <div
        class="viewer-section"
        style="padding-bottom: 0"
    >
        <ConfirmDialog
            :pt="{ root: { style: { fontFamily: 'sans-serif' } } }"
            group="delete-parent"
        ></ConfirmDialog>

        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>

            <Button
                class="add-button"
                style="min-width: 15rem"
                @click="openEditor!(props.componentName)"
            >
                <span><i class="pi pi-plus-circle"></i></span>
                <span>{{$gettext('Add Hierarchical Parent')}}</span>
            </Button>
        </div>

        <div
            v-if="props.data.length"
            style="overflow-x: auto"
        >
            <div class="lineage-section">
                <div
                    v-for="(hierarchy, index) in props.data"
                    :key="index"
                    class="lineage-item"
                >
                    <div style="margin-bottom: 0.5rem">
                        <span
                            style="
                                color: var(--p-neutral-500);
                                font-weight: var(--p-lingo-font-weight-normal);
                                font-size: var(--p-lingo-font-size-medium);
                            "
                        >
                            {{ $gettext("Lineage " + (index + 1)) }}
                        </span>
                    </div>
                    <div
                        v-for="(item, subindex) in hierarchy.searchResults"
                        :key="item.id"
                        class="section-item"
                    >
                        <span
                            :class="getIcon(item)"
                            :style="{
                                'margin-inline-start': subindex * 2 + 'rem',
                            }"
                        ></span>
                        <span style="margin-inline-start: 0.5rem">
                            {{
                                getItemLabel(
                                    item,
                                    selectedLanguage.code,
                                    systemLanguage.code,
                                ).value
                            }}
                        </span>
                        <div
                            v-if="
                                subindex === hierarchy.searchResults.length - 1
                            "
                            style="margin-inline-start: 0.5rem; display: flex"
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
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div
            v-else
            style="
                padding-top: 0.5rem;
                font-size: var(--p-lingo-font-size-smallnormal);
                color: var(--p-inputtext-placeholder-color);
            "
        >
            {{ $gettext("No hierarchical parents were found.") }}
        </div>
    </div>
</template>

<style scoped>
.lineage-section {
    margin-inline-start: 1rem;
    margin-top: 1rem;
    margin-bottom: 1rem;
    display: flex;
    flex-direction: row;
    align-items: start;
    width: fit-content;
}

.lineage-item {
    margin-inline-end: 4rem;
}

.section-item {
    display: flex;
    height: 100%;
    align-items: center;
    min-height: 2.5rem;
    white-space: nowrap;
}
</style>
