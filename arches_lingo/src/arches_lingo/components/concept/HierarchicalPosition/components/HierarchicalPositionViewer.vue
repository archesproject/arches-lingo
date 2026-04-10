<script setup lang="ts">
import { inject, computed, ref } from "vue";
import { useGettext } from "vue3-gettext";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";
import { storeToRefs } from "pinia";

import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";
import Tag from "primevue/tag";

import { deleteLingoTile } from "@/arches_lingo/api.ts";
import { getConceptIcon } from "@/arches_lingo/utils.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import type {
    SearchResultItem,
    SearchResultHierarchy,
} from "@/arches_lingo/types.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    SCHEME_ICON,
} from "@/arches_lingo/constants.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

interface RelationshipGroup {
    tileid: string | undefined;
    isTopConcept: boolean;
    parentConcept: SearchResultItem | undefined;
    lineages: SearchResultHierarchy[];
}

const props = defineProps<{
    componentName: string;
    data: SearchResultHierarchy[];
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId: string | undefined;
    sectionTitle: string;
    scheme?: string;
}>();
const { $gettext, interpolate } = useGettext();
const confirm = useConfirm();
const toast = useToast();

const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

const openEditor =
    inject<(componentName: string, tileId?: string) => void>("openEditor");

const updateAfterComponentDeletion = inject<
    (componentName: string, tileId: string) => void
>("updateAfterComponentDeletion");

const refreshReportSection = inject<(componentName: string) => void>(
    "refreshReportSection",
);

const refreshSchemeHierarchy = inject<() => void>("refreshSchemeHierarchy");

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

const isCreateDisabled = computed(() => {
    return Boolean(
        !props.resourceInstanceId || !canEditResourceInstances.value,
    );
});

const createTooltipText = computed(() => {
    if (!isCreateDisabled.value) {
        return "";
    }

    if (!props.resourceInstanceId) {
        return $gettext(
            "Create a Concept Label before adding hierarchical parents",
        );
    }

    return $gettext(
        "This concept is not editable in its current lifecycle state",
    );
});
const { isEditor } = useUserStore();
const isDeletePending = ref(false);

const relationshipGroups = computed<RelationshipGroup[]>(() => {
    const groupMap = new Map<string, RelationshipGroup>();

    for (const hierarchy of props.data) {
        const groupKey = hierarchy.tileid ?? "no-tile";

        if (!groupMap.has(groupKey)) {
            const parentIndex = hierarchy.searchResults.length - 2;
            const parentConcept =
                parentIndex >= 0
                    ? hierarchy.searchResults[parentIndex]
                    : undefined;

            groupMap.set(groupKey, {
                tileid: hierarchy.tileid,
                isTopConcept: Boolean(hierarchy.isTopConcept),
                parentConcept,
                lineages: [],
            });
        }

        groupMap.get(groupKey)!.lineages.push(hierarchy);
    }

    return Array.from(groupMap.values());
});

function getIcon(item: SearchResultItem) {
    //TODO need a better way to determine if item is a scheme or not
    return item.id === props.scheme ? SCHEME_ICON : getConceptIcon(item);
}

function getItemRoute(item: SearchResultItem) {
    return item.id === props.scheme
        ? { name: routeNames.scheme, params: { id: item.id } }
        : { name: routeNames.concept, params: { id: item.id } };
}

function getParentLabel(group: RelationshipGroup): string {
    if (!group.parentConcept) {
        return $gettext("Unknown Parent");
    }
    return getItemLabel(
        group.parentConcept,
        selectedLanguage.value.code,
        systemLanguage.value.code,
    ).value;
}

function getTopConceptOfLabel(group: RelationshipGroup): string {
    return interpolate(
        $gettext("Top Concept Of: %{parent}"),
        { parent: getParentLabel(group) },
        true,
    );
}

function getBroaderConceptLabel(group: RelationshipGroup): string {
    return interpolate(
        $gettext("Broader Concept: %{parent}"),
        { parent: getParentLabel(group) },
        true,
    );
}

function confirmDelete(group: RelationshipGroup) {
    if (!group.tileid) return;
    const representativeLineage = group.lineages[0];
    confirm.require({
        header: $gettext("Confirmation"),
        message: $gettext(
            "Are you sure you want to delete relationship to parent?",
        ),
        group: "delete-parent",
        data: { hierarchy: representativeLineage },
    } as object);
}

async function deleteSectionValue(hierarchy: SearchResultHierarchy) {
    if (relationshipGroups.value.length === 1) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to delete data."),
            detail: $gettext("Cannot delete the last relationship."),
        });
        return;
    }

    try {
        isDeletePending.value = true;

        await deleteLingoTile(
            props.graphSlug,
            props.nodegroupAlias,
            hierarchy.tileid!,
        );

        refreshSchemeHierarchy!();
        refreshReportSection!(props.componentName);
        updateAfterComponentDeletion!(props.componentName, hierarchy.tileid!);

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

function getTreeNodeStyle(depth: number) {
    const indentation = `${depth * 1.25}rem`;
    const connectorLeft = `${(depth - 1) * 1.25 + 0.35}rem`;

    return {
        "padding-inline-start": indentation,
        "--tree-connector-left": connectorLeft,
    };
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
                            @click="
                                () => deleteSectionValue(message.data.hierarchy)
                            "
                        />
                    </div>
                </div>
            </template>
        </ConfirmDialog>

        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>

            <Button
                v-if="isEditor"
                v-tooltip.top="{
                    disabled: Boolean(!isCreateDisabled),
                    value: createTooltipText,
                    showDelay: 300,
                    pt: {
                        text: {
                            style: { fontFamily: 'var(--p-lingo-font-family)' },
                        },
                        arrow: { style: { display: 'none' } },
                    },
                }"
                :disabled="isCreateDisabled"
                :label="$gettext('Add Hierarchical Parent')"
                class="add-button wide"
                icon="pi pi-plus-circle"
                @click="openEditor!(props.componentName)"
            ></Button>
        </div>

        <div
            v-if="props.data.length"
            style="overflow-x: auto; margin-top: 0.5rem"
        >
            <div
                v-for="(group, groupIndex) in relationshipGroups"
                :key="group.tileid ?? groupIndex"
                class="relationship-group"
            >
                <div class="relationship-group-header">
                    <span class="relationship-group-label">
                        <span
                            v-if="group.parentConcept"
                            :class="getIcon(group.parentConcept)"
                        />

                        <span v-if="group.isTopConcept">
                            {{ getTopConceptOfLabel(group) }}
                        </span>
                        <span v-else>
                            {{ getBroaderConceptLabel(group) }}
                        </span>

                        <Tag
                            v-if="group.lineages.length > 1"
                            :value="
                                $gettext('%{count} paths', {
                                    count: String(group.lineages.length),
                                })
                            "
                            severity="secondary"
                            class="path-count-badge"
                        />
                    </span>
                    <div
                        v-if="isEditor"
                        class="relationship-group-actions"
                    >
                        <div class="button-container">
                            <Button
                                v-if="canEditResourceInstances"
                                class="controls edit-button"
                                icon="pi pi-file-edit"
                                variant="text"
                                :aria-label="$gettext('edit')"
                                :disabled="group.isTopConcept"
                                @click="
                                    openEditor!(componentName, group.tileid)
                                "
                            />
                            <Button
                                v-if="group.tileid && canEditResourceInstances"
                                class="controls delete-button"
                                icon="pi pi-trash"
                                variant="text"
                                :aria-label="$gettext('delete')"
                                @click="confirmDelete(group)"
                            />
                        </div>
                    </div>
                </div>
                <div class="lineage-paths">
                    <template
                        v-for="(hierarchy, lineageIndex) in group.lineages"
                        :key="lineageIndex"
                    >
                        <div class="lineage-path">
                            <div
                                v-for="(item, depth) in hierarchy.searchResults"
                                :key="item.id"
                                class="tree-node"
                                :style="getTreeNodeStyle(depth)"
                            >
                                <span
                                    :class="getIcon(item)"
                                    class="tree-node-icon"
                                />
                                <span
                                    v-if="item.id === props.resourceInstanceId"
                                    class="tree-node-label tree-node-label-current"
                                >
                                    {{
                                        getItemLabel(
                                            item,
                                            selectedLanguage.code,
                                            systemLanguage.code,
                                        ).value
                                    }}
                                </span>
                                <RouterLink
                                    v-else
                                    :to="getItemRoute(item)"
                                    class="tree-node-label"
                                >
                                    {{
                                        getItemLabel(
                                            item,
                                            selectedLanguage.code,
                                            systemLanguage.code,
                                        ).value
                                    }}
                                </RouterLink>
                            </div>
                        </div>
                    </template>
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
.relationship-group {
    margin-bottom: 0.5rem;
    border-radius: 0.25rem;
    padding: 0.75rem 1rem;
    overflow-x: auto;
}

.relationship-group-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: thin solid var(--p-inputtext-border-color);
    padding-bottom: 0.5rem;
    margin-bottom: 0.5rem;
}

.relationship-group-label {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    font-weight: var(--p-lingo-font-weight-semibold, 600);
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
}

.relationship-group-actions {
    display: flex;
    align-items: center;
    flex-shrink: 0;
}

.path-count-badge {
    font-size: var(--p-lingo-font-size-xsmall, 0.75rem);
    font-weight: var(--p-lingo-font-weight-normal, 400);
    color: var(--p-neutral-600);
    background: var(--p-neutral-300);
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    white-space: nowrap;
}

.lineage-paths {
    margin-top: 0.5rem;
}

.lineage-path {
    padding-inline-start: 0.5rem;
    padding-bottom: 1rem;
}

.lineage-divider {
    border-top: thin dashed var(--p-inputtext-border-color);
    margin: 0.5rem 0;
}

.tree-node {
    display: flex;
    align-items: center;
    min-height: 1.75rem;
    position: relative;
    white-space: nowrap;
}

.tree-node:not(:first-child)::before {
    content: "";
    position: absolute;
    left: var(--tree-connector-left);
    top: 0;
    bottom: 50%;
    width: 0.9rem;
    border-inline-start: thin solid var(--p-inputtext-border-color);
    border-bottom: thin solid var(--p-inputtext-border-color);
    border-end-start-radius: 0.2rem;
}

.tree-node-icon {
    flex-shrink: 0;
    position: relative;
    background-color: var(--p-content-background);
    padding-inline: 0.1rem;
}

.tree-node-label {
    margin-inline-start: 0.5rem;
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-primary-500);
}

.tree-node-label-current {
    color: var(--p-text-color);
    font-weight: var(--p-lingo-font-weight-semibold, 600);
}

.button-container {
    display: flex;
    gap: 0.25rem;
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

.controls {
    padding: 0.25rem;
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
    border: 1px solid var(--p-button-danger-border-color);
    color: var(--p-button-danger-color);
}

.button-container .edit-button:hover {
    background: var(--p-button-primary-hover-background);
    border: 1px solid var(--p-button-primary-hover-border-color);
    color: var(--p-button-primary-hover-color);
}

.button-container .delete-button:hover {
    background: var(--p-button-danger-hover-background);
    border: 1px solid var(--p-button-danger-hover-border-color);
    color: var(--p-button-danger-hover-color);
}
</style>
