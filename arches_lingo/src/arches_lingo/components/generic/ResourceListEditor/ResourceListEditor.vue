<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Column from "primevue/column";
import ConfirmDialog from "primevue/confirmdialog";
import DataTable from "primevue/datatable";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Skeleton from "primevue/skeleton";
import Splitter from "primevue/splitter";
import SplitterPanel from "primevue/splitterpanel";
import Tag from "primevue/tag";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import ComponentEditor from "@/arches_lingo/components/generic/ComponentManager/components/ComponentEditor.vue";
import {
    deleteLingoResource,
    fetchResourceReferenceCount,
} from "@/arches_lingo/api.ts";
import {
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    ERROR,
    SECONDARY,
    SUCCESS,
} from "@/arches_lingo/constants.ts";

import type {
    PaginatedResourceListResponse,
    ResourceSummary,
} from "@/arches_lingo/types";

const PAGE_SIZE = 25;

const props = defineProps<{
    pageTitle: string;
    fetchResources: (
        search: string,
        limit: number,
        offset: number,
    ) => Promise<PaginatedResourceListResponse>;
    showGraphType?: boolean;
    refreshTrigger?: number;
    editorEnabled?: boolean;
}>();

const emit = defineEmits<{
    "select-resource": [resource: ResourceSummary];
}>();

const toast = useToast();
const confirm = useConfirm();
const { $gettext, interpolate, $ngettext } = useGettext();

const isLoading = ref(true);
const resources = ref<ResourceSummary[]>([]);
const totalRecords = ref(0);
const currentPage = ref(0);
const searchQuery = ref("");
const selectedResource = ref<ResourceSummary | null>(null);
const isEditorOpen = ref(false);
const isEditorMaximized = ref(false);
const isCreatingNew = ref(false);
const editorInstanceKey = ref(0);
const pendingSavedResourceInstanceId = ref<string | null>(null);

let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

const editorTitle = computed(() => {
    if (isCreatingNew.value) return $gettext("New Resource");
    if (!selectedResource.value) return "";
    const displayName =
        selectedResource.value.display_name || $gettext("Untitled");
    return $gettext(`Now Editing: ${displayName}`);
});

watch(
    () => props.fetchResources,
    () => {
        currentPage.value = 0;
        loadResources();
    },
    { immediate: true },
);

watch(
    () => props.refreshTrigger,
    () => {
        loadResources();
    },
);

async function loadResources() {
    isLoading.value = true;
    try {
        const response = await props.fetchResources(
            searchQuery.value,
            PAGE_SIZE,
            currentPage.value * PAGE_SIZE,
        );
        resources.value = response.results;
        totalRecords.value = response.count;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch resources"),
            detail: error instanceof Error ? error.message : undefined,
        });
    }

    const resourceIdToSync =
        pendingSavedResourceInstanceId.value ??
        selectedResource.value?.resourceinstanceid;
    if (resourceIdToSync) {
        const refreshed = resources.value.find(
            (resource) => resource.resourceinstanceid === resourceIdToSync,
        );
        if (refreshed) {
            selectedResource.value = refreshed;
        }
    }
    pendingSavedResourceInstanceId.value = null;

    isLoading.value = false;
}

function onPage(event: { first: number; rows: number }) {
    currentPage.value = Math.floor(event.first / event.rows);
    loadResources();
}

function onSearchInput() {
    if (searchDebounceTimer) {
        clearTimeout(searchDebounceTimer);
    }
    searchDebounceTimer = setTimeout(() => {
        currentPage.value = 0;
        loadResources();
    }, 400);
}

function onRowSelect(event: { data: ResourceSummary }) {
    isCreatingNew.value = false;
    selectedResource.value = event.data;
    if (props.editorEnabled !== false) {
        isEditorOpen.value = true;
        editorInstanceKey.value++;
    }
    emit("select-resource", event.data);
}

function openBlankEditor() {
    selectedResource.value = null;
    isCreatingNew.value = true;
    isEditorOpen.value = true;
    editorInstanceKey.value++;
}

function closeEditor() {
    isEditorOpen.value = false;
    isEditorMaximized.value = false;
    selectedResource.value = null;
    isCreatingNew.value = false;
}

async function confirmDeleteResource(resource: ResourceSummary) {
    let referenceCount = 0;
    try {
        referenceCount = await fetchResourceReferenceCount(
            resource.resourceinstanceid,
        );
    } catch {
        // If the count fetch fails, proceed with 0 to not block the delete
    }

    const resourceName = resource.display_name || $gettext("Untitled");
    const baseMessage = interpolate(
        $gettext('Are you sure you want to delete "%{name}"?'),
        { name: resourceName },
    );
    const referenceWarning = referenceCount
        ? interpolate(
              $ngettext(
                  "This resource is referenced by %{count} other resource. That reference will be lost.",
                  "This resource is referenced by %{count} other resources. Those references will be lost.",
                  referenceCount,
              ),
              { count: referenceCount },
          )
        : "";

    const message = referenceWarning
        ? `${baseMessage}\n\n${referenceWarning}`
        : baseMessage;

    confirm.require({
        header: $gettext("Delete Resource"),
        message,
        group: "delete-resource",
        acceptProps: {
            label: $gettext("Delete"),
            severity: DANGER,
        },
        rejectProps: {
            label: $gettext("Cancel"),
            severity: SECONDARY,
            outlined: true,
        },
        accept: async () => {
            try {
                await deleteLingoResource(
                    resource.graph_slug,
                    resource.resourceinstanceid,
                );

                if (
                    selectedResource.value?.resourceinstanceid ===
                    resource.resourceinstanceid
                ) {
                    closeEditor();
                }

                toast.add({
                    severity: SUCCESS,
                    life: DEFAULT_TOAST_LIFE,
                    summary: $gettext("Resource deleted"),
                });

                loadResources();
            } catch (error) {
                toast.add({
                    severity: ERROR,
                    life: DEFAULT_ERROR_TOAST_LIFE,
                    summary: $gettext("Failed to delete resource"),
                    detail: error instanceof Error ? error.message : undefined,
                });
            }
        },
    });
}

defineExpose({
    afterSave(savedResourceInstanceId: string) {
        isCreatingNew.value = false;
        pendingSavedResourceInstanceId.value = savedResourceInstanceId;
    },
});
</script>

<template>
    <div class="resource-list-editor">
        <Splitter
            :key="isEditorOpen ? 'open' : 'closed'"
            class="resource-splitter"
        >
            <SplitterPanel
                v-show="!isEditorMaximized"
                :size="isEditorOpen ? 50 : 100"
                :min-size="30"
                class="list-panel"
            >
                <div class="list-panel-content">
                    <div class="list-header">
                        <div class="list-header-toolbar">
                            <h1 class="page-title">{{ pageTitle }}</h1>
                            <div class="header-buttons">
                                <slot
                                    name="list-actions"
                                    :open-blank-editor="openBlankEditor"
                                />
                            </div>
                        </div>
                        <div class="list-header-content">
                            <IconField class="search-field">
                                <InputIcon class="pi pi-search" />
                                <InputText
                                    v-model="searchQuery"
                                    :placeholder="$gettext('Search by name...')"
                                    class="search-input"
                                    @input="onSearchInput"
                                />
                            </IconField>
                        </div>
                    </div>

                    <DataTable
                        :value="resources"
                        :loading="isLoading"
                        :lazy="true"
                        :paginator="true"
                        :rows="PAGE_SIZE"
                        :total-records="totalRecords"
                        :first="currentPage * PAGE_SIZE"
                        :selection="selectedResource"
                        selection-mode="single"
                        data-key="resourceinstanceid"
                        striped-rows
                        class="resource-table"
                        @page="onPage"
                        @row-select="onRowSelect"
                        @row-unselect.stop
                    >
                        <Column
                            field="display_name"
                            :header="$gettext('Name')"
                            class="name-column"
                        >
                            <template #body="{ data }">
                                <span v-if="data.display_name">{{
                                    data.display_name
                                }}</span>
                                <span
                                    v-else
                                    class="unnamed-resource"
                                    >{{ $gettext("Untitled") }}</span
                                >
                            </template>
                            <template #loading>
                                <Skeleton />
                            </template>
                        </Column>

                        <Column
                            v-if="showGraphType"
                            field="graph_name"
                            :header="$gettext('Type')"
                            class="type-column"
                        >
                            <template #body="{ data }">
                                <Tag
                                    :value="data.graph_name"
                                    severity="info"
                                />
                            </template>
                            <template #loading>
                                <Skeleton />
                            </template>
                        </Column>

                        <Column
                            v-if="editorEnabled"
                            class="actions-column"
                        >
                            <template #body="{ data }">
                                <Button
                                    :aria-label="$gettext('Delete resource')"
                                    icon="pi pi-trash"
                                    severity="danger"
                                    text
                                    rounded
                                    size="small"
                                    class="delete-button"
                                    @click.stop="confirmDeleteResource(data)"
                                />
                            </template>
                        </Column>

                        <template #empty>
                            <div class="empty-message">
                                {{
                                    searchQuery
                                        ? $gettext(
                                              "No resources match the search criteria.",
                                          )
                                        : $gettext(
                                              "No resources have been created yet.",
                                          )
                                }}
                            </div>
                        </template>
                    </DataTable>
                </div>
            </SplitterPanel>

            <SplitterPanel
                v-if="isEditorOpen"
                :size="50"
                :min-size="30"
                class="editor-panel"
            >
                <ComponentEditor
                    :key="editorInstanceKey"
                    :is-editor-maximized="isEditorMaximized"
                    :is-form-editor="true"
                    :header-title="editorTitle"
                    @maximize="isEditorMaximized = true"
                    @minimize="isEditorMaximized = false"
                    @close="closeEditor"
                >
                    <div class="form-header">
                        <h3>{{ editorTitle }}</h3>
                        <div class="form-description">
                            {{
                                $gettext(
                                    "Add or edit resource name information.",
                                )
                            }}
                        </div>
                    </div>
                    <div class="form-container">
                        <slot
                            name="editor"
                            :resource="selectedResource"
                            :is-creating-new="isCreatingNew"
                        />
                    </div>
                </ComponentEditor>
            </SplitterPanel>
        </Splitter>
    </div>

    <ConfirmDialog
        group="delete-resource"
        class="delete-confirm-dialog"
    >
        <template #message="{ message }">
            <p
                class="delete-confirm-message"
                style="white-space: pre-line"
            >
                {{ message.message }}
            </p>
        </template>
    </ConfirmDialog>
</template>

<style scoped>
.resource-list-editor {
    height: 100%;
    min-height: 0;
}

.resource-splitter {
    height: 100%;
    min-height: 0;
    border: none;
}

.list-panel {
    overflow: auto;
}

.list-panel-content {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
}

.list-header {
    display: flex;
    flex-direction: column;
}

.list-header-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--p-header-toolbar-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    padding: 0.375rem 1rem;
}

.header-buttons {
    display: flex;
    gap: 0.25rem;
    flex-wrap: wrap;
    justify-content: flex-end;
}

.list-header-content {
    padding: 0.75rem 1rem;
}

.page-title {
    margin: 0;
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
}

.search-field {
    width: 100%;
}

.search-input {
    width: 100%;
    border-radius: 0.125rem;
}

.resource-table {
    flex: 1;
    min-height: 0;
    padding: 0 1rem;
}

.unnamed-resource {
    color: var(--p-inputtext-placeholder-color);
    font-style: italic;
}

.empty-message {
    padding: 2rem;
    text-align: center;
    color: var(--p-inputtext-placeholder-color);
}

.editor-panel {
    overflow: hidden;
}

:deep(.type-column) {
    width: 8rem;
}

:deep(.actions-column) {
    width: 3rem;
    padding: 0;
    text-align: center;
}

.delete-button {
    width: 2rem;
    height: 2rem;
}

.delete-confirm-message {
    margin: 0;
    line-height: 1.5;
}

:deep(.p-inputtext),
:deep(.p-multiselect),
:deep(.p-textarea),
:deep(.p-treeselect),
:deep(.p-select) {
    border-radius: 0.125rem;
}

:deep(.p-inputtext) {
    font-size: 0.875rem !important;
}

:deep(.p-treeselect-label) {
    font-size: 0.875rem !important;
}
</style>
