<script setup lang="ts">
import { ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";
import { useConfirm } from "primevue/useconfirm";

import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";

import {
    fetchSavedSearches,
    createSavedSearch,
    deleteSavedSearch,
} from "@/arches_lingo/api.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    SUCCESS,
    DEFAULT_TOAST_LIFE,
    DANGER,
    SECONDARY,
} from "@/arches_lingo/constants.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

import type {
    AdvancedSearchQuery,
    SavedSearchItem,
} from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();
const toast = useToast();
const confirm = useConfirm();
const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

const props = defineProps<{
    currentQuery: AdvancedSearchQuery;
}>();

const emit = defineEmits<{
    (event: "load-search", query: AdvancedSearchQuery): void;
}>();

const DELETE_SAVED_SEARCH_CONFIRM_GROUP = "delete-saved-search";

const savedSearches = ref<SavedSearchItem[]>([]);
const showSaveDialog = ref(false);
const newSearchName = ref("");
const isLoading = ref(false);

async function loadSavedSearches() {
    try {
        const result = await fetchSavedSearches();
        savedSearches.value = result.data;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to load saved searches."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

async function saveCurrentSearch() {
    const name = newSearchName.value.trim();
    if (!name) return;

    isLoading.value = true;
    try {
        const saved = await createSavedSearch(name, props.currentQuery);
        savedSearches.value.unshift(saved);
        showSaveDialog.value = false;
        newSearchName.value = "";
        toast.add({
            severity: SUCCESS,
            life: DEFAULT_TOAST_LIFE,
            summary: $gettext("Search saved."),
        });
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to save search."),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
    }
}

async function deleteSearch(search: SavedSearchItem) {
    try {
        await deleteSavedSearch(search.id);
        savedSearches.value = savedSearches.value.filter(
            (item) => item.id !== search.id,
        );
        toast.add({
            severity: SUCCESS,
            life: DEFAULT_TOAST_LIFE,
            summary: $gettext("Search deleted."),
        });
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to delete search."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

function confirmDeleteSearch(search: SavedSearchItem) {
    confirm.require({
        group: DELETE_SAVED_SEARCH_CONFIRM_GROUP,
        header: $gettext("Delete saved search?"),
        message: $gettext(
            'The saved search "%{name}" will be deleted.',
            { name: search.name },
            true,
        ),
        accept: () => deleteSearch(search),
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

function loadSearch(search: SavedSearchItem) {
    emit("load-search", search.query);
}

watch(
    isAnonymous,
    (isAnonymous) => {
        if (!isAnonymous) {
            loadSavedSearches();
        }
    },
    { immediate: true },
);
</script>

<template>
    <div class="saved-searches">
        <div class="section-actions">
            <Button
                :label="$gettext('Save Current')"
                icon="pi pi-save"
                size="small"
                @click="showSaveDialog = true"
            />
        </div>

        <div
            v-if="savedSearches.length === 0"
            class="empty-message"
        >
            {{ $gettext("No saved searches yet.") }}
        </div>

        <div
            v-for="search in savedSearches"
            :key="search.id"
            class="saved-search-item"
        >
            <Button
                text
                plain
                class="search-info"
                :pt="{
                    root: {
                        style: {
                            flexDirection: 'column',
                            alignItems: 'flex-start',
                            justifyContent: 'flex-start',
                            padding: '0.375rem 0',
                            gap: '0.125rem',
                        },
                    },
                }"
                @click="loadSearch(search)"
            >
                <span class="search-name">{{ search.name }}</span>
                <span class="search-date">
                    {{ new Date(search.updated).toLocaleDateString() }}
                </span>
            </Button>
            <Button
                icon="pi pi-trash"
                severity="danger"
                text
                rounded
                size="small"
                :aria-label="
                    $gettext('Delete %{name}', { name: search.name }, true)
                "
                @click="confirmDeleteSearch(search)"
            />
        </div>

        <Dialog
            v-model:visible="showSaveDialog"
            :header="$gettext('Save Search')"
            modal
            :style="{ width: 'min(25rem, 100%)' }"
        >
            <div class="save-dialog-content">
                <label for="search-name">{{ $gettext("Name") }}</label>
                <InputText
                    id="search-name"
                    v-model="newSearchName"
                    :placeholder="$gettext('Enter search name')"
                    autofocus
                    class="search-name-input"
                    @keyup.enter="saveCurrentSearch"
                />
            </div>
            <template #footer>
                <Button
                    :label="$gettext('Cancel')"
                    text
                    @click="showSaveDialog = false"
                />
                <Button
                    :label="$gettext('Save')"
                    icon="pi pi-check"
                    :loading="isLoading"
                    :disabled="!newSearchName.trim()"
                    @click="saveCurrentSearch"
                />
            </template>
        </Dialog>
        <ConfirmDialog :group="DELETE_SAVED_SEARCH_CONFIRM_GROUP" />
    </div>
</template>

<style scoped>
.saved-searches {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    font-family: var(--p-lingo-font-family);
}

.section-actions {
    display: flex;
    justify-content: flex-end;
    padding-bottom: 0.5rem;
    border-bottom: 0.0625rem solid var(--p-lingo-divider-color);
}

.section-actions :deep(.p-button) {
    font-size: var(--p-lingo-font-size-xsmall);
    font-weight: var(--p-lingo-font-weight-normal);
    border-radius: 0.125rem;
}

.empty-message {
    text-align: center;
    padding: 1rem;
    color: var(--p-text-muted-color);
    font-size: var(--p-lingo-font-size-small);
}

.saved-search-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem;
    border-radius: 0.125rem;
    cursor: pointer;
}

.saved-search-item:hover {
    background-color: var(--p-highlight-background);
}

.search-info {
    flex: 1;
    min-width: 0;
    font-family: var(--p-lingo-font-family);
}

.search-name {
    max-width: 100%;
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-smallnormal);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.search-date {
    font-size: var(--p-lingo-font-size-xsmall);
    color: var(--p-text-muted-color);
}

.save-dialog-content {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.search-name-input {
    width: 100%;
}
</style>
