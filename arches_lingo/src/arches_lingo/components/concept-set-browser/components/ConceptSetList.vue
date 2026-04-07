<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Textarea from "primevue/textarea";

import type { ConceptSetItem } from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();

defineProps<{
    conceptSets: ConceptSetItem[];
}>();

const emit = defineEmits<{
    (event: "select-set", setItem: ConceptSetItem): void;
    (event: "create-set", name: string, description: string): void;
    (event: "delete-set", setItem: ConceptSetItem): void;
}>();

const showCreateDialog = ref(false);
const newSetName = ref("");
const newSetDescription = ref("");

function submitCreateSet() {
    const name = newSetName.value.trim();
    if (!name) return;
    emit("create-set", name, newSetDescription.value);
    showCreateDialog.value = false;
    newSetName.value = "";
    newSetDescription.value = "";
}

function cancelCreateDialog() {
    showCreateDialog.value = false;
    newSetName.value = "";
    newSetDescription.value = "";
}
</script>

<template>
    <div class="concept-set-list">
        <div class="list-actions">
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

        <ul
            v-else
            class="sets-list"
        >
            <li
                v-for="setItem in conceptSets"
                :key="setItem.id"
                class="set-item"
            >
                <button
                    class="set-info"
                    @click="emit('select-set', setItem)"
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
                </button>
                <Button
                    icon="pi pi-trash"
                    severity="danger"
                    text
                    rounded
                    size="small"
                    :aria-label="$gettext('Delete set')"
                    @click="emit('delete-set', setItem)"
                />
            </li>
        </ul>

        <Dialog
            v-model:visible="showCreateDialog"
            :header="$gettext('New Concept Set')"
            modal
            :style="{ width: '25rem' }"
        >
            <div class="dialog-content">
                <label for="new-set-name">{{ $gettext("Name") }}</label>
                <InputText
                    id="new-set-name"
                    v-model="newSetName"
                    :placeholder="$gettext('Set name')"
                    autofocus
                    class="full-width"
                />
                <label for="new-set-description">
                    {{ $gettext("Description") }}
                </label>
                <Textarea
                    id="new-set-description"
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
                    @click="cancelCreateDialog"
                />
                <Button
                    :label="$gettext('Create')"
                    icon="pi pi-check"
                    :disabled="!newSetName.trim()"
                    @click="submitCreateSet"
                />
            </template>
        </Dialog>
    </div>
</template>

<style scoped>
.concept-set-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    height: 100%;
    overflow: hidden;
    font-family: var(--p-lingo-font-family);
}

.list-actions {
    display: flex;
    justify-content: flex-end;
    padding: 0.5rem;
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
    flex-shrink: 0;
}

.list-actions :deep(.p-button) {
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

.sets-list {
    flex: 1 1 auto;
    overflow-y: auto;
    list-style: none;
    margin: 0;
    padding: 0;
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

.set-info {
    flex: 1;
    min-width: 0;
    cursor: pointer;
    background: none;
    border: none;
    padding: 0;
    text-align: left;
    color: var(--p-text-color);
    font-family: var(--p-lingo-font-family);
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
