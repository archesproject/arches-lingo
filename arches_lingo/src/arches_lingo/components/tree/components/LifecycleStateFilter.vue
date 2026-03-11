<script setup lang="ts">
import { computed, useTemplateRef } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Popover from "primevue/popover";

import type { PopoverMethods } from "primevue/popover";

interface LifecycleState {
    id: string;
    name: string;
}

const props = defineProps<{
    lifecycleStates: LifecycleState[];
    selectedStateIds: string[];
}>();

const emit = defineEmits<{
    "update:selectedStateIds": [value: string[]];
}>();

const { $gettext } = useGettext();

const FILTER_BY_LIFECYCLE_STATE = $gettext("Filter by lifecycle state");
const ALL_STATES = $gettext("All states");
const LIFECYCLE_STATE_FILTER_LABEL = $gettext("Lifecycle state filter");

const popoverRef = useTemplateRef<PopoverMethods>("popover");

const isFilterActive = computed(() => props.selectedStateIds.length > 0);

const allStatesChecked = computed(() => !isFilterActive.value);

const someStatesChecked = computed(
    () =>
        isFilterActive.value &&
        props.selectedStateIds.length < props.lifecycleStates.length,
);

function isStateChecked(stateId: string): boolean {
    return !isFilterActive.value || props.selectedStateIds.includes(stateId);
}

function handleSelectAllToggle() {
    if (isFilterActive.value) {
        emit("update:selectedStateIds", []);
    }
}

function handleStateToggle(stateId: string) {
    const currentlyChecked = isStateChecked(stateId);

    if (currentlyChecked) {
        let newSelectedIds: string[];

        if (!isFilterActive.value) {
            newSelectedIds = props.lifecycleStates
                .map((state) => state.id)
                .filter((id) => id !== stateId);
        } else {
            newSelectedIds = props.selectedStateIds.filter(
                (id) => id !== stateId,
            );
        }

        if (newSelectedIds.length > 0) {
            emit("update:selectedStateIds", newSelectedIds);
        }
    } else {
        const newSelectedIds = [...props.selectedStateIds, stateId];

        if (newSelectedIds.length === props.lifecycleStates.length) {
            emit("update:selectedStateIds", []);
        } else {
            emit("update:selectedStateIds", newSelectedIds);
        }
    }
}

function openPopover(event: MouseEvent) {
    popoverRef.value!.toggle(event);
}
</script>

<template>
    <div class="lifecycle-state-filter">
        <Button
            :icon="isFilterActive ? 'pi pi-filter-fill' : 'pi pi-filter'"
            :class="{ 'filter-active': isFilterActive }"
            :aria-label="FILTER_BY_LIFECYCLE_STATE"
            :title="FILTER_BY_LIFECYCLE_STATE"
            text
            rounded
            @click="openPopover"
        />

        <Popover ref="popover">
            <div class="lifecycle-filter-panel">
                <p class="lifecycle-filter-heading">
                    {{ LIFECYCLE_STATE_FILTER_LABEL }}
                </p>

                <div class="lifecycle-filter-option">
                    <Checkbox
                        :model-value="allStatesChecked"
                        :indeterminate="someStatesChecked"
                        binary
                        input-id="lifecycle-state-all"
                        @update:model-value="handleSelectAllToggle"
                    />
                    <label for="lifecycle-state-all">{{ ALL_STATES }}</label>
                </div>

                <div
                    v-for="state in lifecycleStates"
                    :key="state.id"
                    class="lifecycle-filter-option"
                >
                    <Checkbox
                        :model-value="isStateChecked(state.id)"
                        binary
                        :input-id="`lifecycle-state-${state.id}`"
                        @update:model-value="() => handleStateToggle(state.id)"
                    />
                    <label :for="`lifecycle-state-${state.id}`">
                        {{ state.name }}
                    </label>
                </div>
            </div>
        </Popover>
    </div>
</template>

<style scoped>
.lifecycle-filter-panel {
    min-width: 13rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.lifecycle-filter-heading {
    margin: 0 0 0.25rem;
    font-weight: 600;
    font-size: 0.875rem;
    padding-bottom: 0.5rem;
    border-bottom: 0.0625rem solid var(--p-menubar-border-color);
}

.lifecycle-filter-option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
}

.lifecycle-filter-option label {
    cursor: pointer;
    font-size: 0.875rem;
}

.lifecycle-state-filter :deep(.p-button.filter-active) {
    color: var(--p-primary-color);
}
</style>
