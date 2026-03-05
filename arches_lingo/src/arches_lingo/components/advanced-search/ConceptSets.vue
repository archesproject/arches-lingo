<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Textarea from "primevue/textarea";

import {
    fetchConceptSets,
    createConceptSet,
    deleteConceptSet,
    addToConceptSet,
    removeFromConceptSet,
} from "@/arches_lingo/api.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    ERROR,
    SUCCESS,
} from "@/arches_lingo/constants.ts";

import type { ConceptSetItem } from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();
const toast = useToast();

defineProps<{
    selectedConceptIds: Set<string>;
    activeConceptSetId: number | null;
}>();

const emit = defineEmits<{
    (event: "load-set", conceptSetId: number): void;
    (event: "sets-updated", sets: ConceptSetItem[]): void;
    (event: "concepts-removed"): void;
}>();

const conceptSets = ref<ConceptSetItem[]>([]);
const showCreateDialog = ref(false);
const showAddToSetDialog = ref(false);
const newSetName = ref("");
const newSetDescription = ref("");
const targetSetId = ref<number | null>(null);
const isLoading = ref(false);

async function loadConceptSets() {
    try {
        const result = await fetchConceptSets();
        conceptSets.value = result.data;
        emit("sets-updated", conceptSets.value);
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to load concept sets."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

async function createNewSet() {
    const name = newSetName.value.trim();
    if (!name) return;

    isLoading.value = true;
    try {
        const created = await createConceptSet(name, newSetDescription.value);
        conceptSets.value.unshift(created);
        emit("sets-updated", conceptSets.value);
        showCreateDialog.value = false;
        newSetName.value = "";
        newSetDescription.value = "";
        toast.add({
            severity: SUCCESS,
            life: DEFAULT_TOAST_LIFE,
            summary: $gettext("Concept set created."),
        });
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to create concept set."),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
    }
}

async function deleteSet(setItem: ConceptSetItem) {
    try {
        await deleteConceptSet(setItem.id);
        conceptSets.value = conceptSets.value.filter(
            (item) => item.id !== setItem.id,
        );
        emit("sets-updated", conceptSets.value);
        toast.add({
            severity: SUCCESS,
            life: DEFAULT_TOAST_LIFE,
            summary: $gettext("Concept set deleted."),
        });
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to delete concept set."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

function handleAddToSet(selectedIds: Set<string>) {
    if (targetSetId.value === null || selectedIds.size === 0) return;

    isLoading.value = true;
    addToConceptSet(targetSetId.value, Array.from(selectedIds))
        .then((result) => {
            showAddToSetDialog.value = false;
            targetSetId.value = null;
            toast.add({
                severity: SUCCESS,
                life: DEFAULT_TOAST_LIFE,
                summary: $gettext("%{count} concepts added to set.", {
                    count: String(result.added),
                }),
            });
            loadConceptSets();
        })
        .catch((error) => {
            toast.add({
                severity: ERROR,
                life: DEFAULT_ERROR_TOAST_LIFE,
                summary: $gettext("Failed to add concepts to set."),
                detail: error instanceof Error ? error.message : undefined,
            });
        })
        .finally(() => {
            isLoading.value = false;
        });
}

function loadSet(setItem: ConceptSetItem) {
    emit("load-set", setItem.id);
}

async function handleRemoveFromSet(setId: number, selectedIds: Set<string>) {
    if (selectedIds.size === 0) return;
    isLoading.value = true;
    try {
        await removeFromConceptSet(setId, Array.from(selectedIds));
        toast.add({
            severity: SUCCESS,
            life: DEFAULT_TOAST_LIFE,
            summary: $gettext("%{count} concepts removed from set.", {
                count: String(selectedIds.size),
            }),
        });
        await loadConceptSets();
        emit("concepts-removed");
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to remove concepts from set."),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
    }
}

defineExpose({
    handleAddToSet,
    loadConceptSets,
});

onMounted(loadConceptSets);
</script>

<template>
    <div class="concept-sets">
        <div class="section-actions">
            <Button
                :label="$gettext('Add to Set')"
                icon="pi pi-plus-circle"
                size="small"
                :disabled="selectedConceptIds.size === 0"
                @click="showAddToSetDialog = true"
            />
            <Button
                v-if="activeConceptSetId !== null"
                :label="$gettext('Remove from Set')"
                icon="pi pi-minus-circle"
                size="small"
                severity="danger"
                :disabled="selectedConceptIds.size === 0"
                :loading="isLoading"
                @click="
                    handleRemoveFromSet(activeConceptSetId!, selectedConceptIds)
                "
            />
            <Button
                :label="$gettext('New Set')"
                icon="pi pi-folder"
                size="small"
                outlined
                @click="showCreateDialog = true"
            />
        </div>

        <div
            v-if="conceptSets.length === 0"
            class="empty-message"
        >
            {{ $gettext("No concept sets yet.") }}
        </div>

        <div
            v-for="setItem in conceptSets"
            :key="setItem.id"
            class="set-item"
            :class="{ 'set-item--active': setItem.id === activeConceptSetId }"
        >
            <div
                class="set-info"
                @click="loadSet(setItem)"
            >
                <div class="set-name">
                    <i
                        class="pi pi-folder"
                        aria-hidden="true"
                    />
                    {{ setItem.name }}
                </div>
                <div class="set-meta">
                    {{
                        $gettext("%{count} concepts", {
                            count: String(setItem.member_count),
                        })
                    }}
                    &middot;
                    {{ new Date(setItem.updated).toLocaleDateString() }}
                </div>
                <div
                    v-if="setItem.description"
                    class="set-description"
                >
                    {{ setItem.description }}
                </div>
            </div>
            <Button
                icon="pi pi-trash"
                severity="danger"
                text
                rounded
                size="small"
                :aria-label="$gettext('Delete')"
                @click="deleteSet(setItem)"
            />
        </div>

        <!-- Create Set Dialog -->
        <Dialog
            v-model:visible="showCreateDialog"
            :header="$gettext('New Concept Set')"
            modal
            :style="{ width: '25rem' }"
        >
            <div class="dialog-content">
                <label for="set-name">{{ $gettext("Name") }}</label>
                <InputText
                    id="set-name"
                    v-model="newSetName"
                    :placeholder="$gettext('Set name')"
                    autofocus
                    class="full-width"
                />

                <label for="set-description">{{
                    $gettext("Description")
                }}</label>
                <Textarea
                    id="set-description"
                    v-model="newSetDescription"
                    :placeholder="$gettext('Optional description')"
                    :rows="3"
                    class="full-width"
                />
            </div>
            <template #footer>
                <Button
                    :label="$gettext('Cancel')"
                    text
                    @click="showCreateDialog = false"
                />
                <Button
                    :label="$gettext('Create')"
                    icon="pi pi-check"
                    :loading="isLoading"
                    :disabled="!newSetName.trim()"
                    @click="createNewSet"
                />
            </template>
        </Dialog>

        <!-- Add to Set Dialog -->
        <Dialog
            v-model:visible="showAddToSetDialog"
            :header="
                $gettext('Add %{count} concepts to set', {
                    count: String(selectedConceptIds.size),
                })
            "
            modal
            :style="{ width: '25rem' }"
        >
            <div class="dialog-content">
                <label for="target-set">{{ $gettext("Select Set") }}</label>
                <Select
                    v-model="targetSetId"
                    :options="conceptSets"
                    option-label="name"
                    option-value="id"
                    :placeholder="$gettext('Choose a concept set')"
                    class="full-width"
                />
            </div>
            <template #footer>
                <Button
                    :label="$gettext('Cancel')"
                    text
                    @click="showAddToSetDialog = false"
                />
                <Button
                    :label="$gettext('Add')"
                    icon="pi pi-plus"
                    :loading="isLoading"
                    :disabled="targetSetId === null"
                    @click="handleAddToSet(selectedConceptIds)"
                />
            </template>
        </Dialog>
    </div>
</template>

<style scoped>
.concept-sets {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    font-family: var(--p-lingo-font-family);
}

.section-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    padding-bottom: 0.5rem;
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
    gap: 0.375rem;
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

.set-item {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    padding: 0.5rem;
    border-radius: 0.125rem;
}

.set-item:hover {
    background-color: var(--p-highlight-background);
}

.set-item--active {
    background-color: var(--p-highlight-background);
    border-left: 0.1875rem solid var(--p-primary-400);
}

.set-info {
    flex: 1;
    min-width: 0;
    cursor: pointer;
}

.set-name {
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-smallnormal);
    display: flex;
    align-items: center;
    gap: 0.375rem;
}

.set-meta {
    font-size: var(--p-lingo-font-size-xsmall);
    color: var(--p-text-muted-color);
    margin-top: 0.125rem;
}

.set-description {
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-text-muted-color);
    margin-top: 0.25rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.dialog-content {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.full-width {
    width: 100%;
}
</style>
