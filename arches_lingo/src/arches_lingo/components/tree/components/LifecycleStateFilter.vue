<script setup lang="ts">
import { computed, useTemplateRef } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Popover from "primevue/popover";

import type { PopoverMethods } from "primevue/popover";
import type { LifecycleState } from "@/arches_lingo/types";

const props = defineProps<{
    lifecycleStates: LifecycleState[];
}>();

const selectedLifecycleStateIds = defineModel<string[]>(
    "selectedLifecycleStateIds",
    { required: true },
);

const { $gettext } = useGettext();

const FILTER_BY_LIFECYCLE_STATE = $gettext("Filter by lifecycle state");
const ALL_STATES = $gettext("All states");
const LIFECYCLE_STATE_FILTER_LABEL = $gettext("Lifecycle state filter");

const popoverRef = useTemplateRef<PopoverMethods>("popover");

const isFilterActive = computed(
    () => selectedLifecycleStateIds.value.length < props.lifecycleStates.length,
);

const allStates = computed({
    get(): boolean {
        return (
            selectedLifecycleStateIds.value.length >=
            props.lifecycleStates.length
        );
    },
    set(checked: boolean) {
        if (checked) {
            selectedLifecycleStateIds.value = props.lifecycleStates.map(
                (state) => state.id,
            );
        } else {
            selectedLifecycleStateIds.value = [];
        }
    },
});

const someStatesChecked = computed(
    () =>
        selectedLifecycleStateIds.value.length > 0 &&
        selectedLifecycleStateIds.value.length < props.lifecycleStates.length,
);

function isStateChecked(stateId: string): boolean {
    return selectedLifecycleStateIds.value.includes(stateId);
}

function setStateChecked(stateId: string, checked: boolean) {
    if (checked) {
        selectedLifecycleStateIds.value = [
            ...selectedLifecycleStateIds.value,
            stateId,
        ];
    } else {
        selectedLifecycleStateIds.value =
            selectedLifecycleStateIds.value.filter((id) => id !== stateId);
    }
}

function openPopover(event: MouseEvent) {
    popoverRef.value?.toggle(event);
}
</script>

<template>
    <div class="lifecycle-state-filter">
        <Button
            :icon="isFilterActive ? 'pi pi-filter-fill' : 'pi pi-filter'"
            :class="{ 'filter-active': isFilterActive }"
            :aria-label="FILTER_BY_LIFECYCLE_STATE"
            :title="FILTER_BY_LIFECYCLE_STATE"
            :text="true"
            :rounded="true"
            @click="openPopover"
        />

        <Popover ref="popover">
            <div class="lifecycle-filter-panel">
                <div class="lifecycle-filter-heading">
                    {{ LIFECYCLE_STATE_FILTER_LABEL }}
                </div>

                <div class="lifecycle-filter-option">
                    <Checkbox
                        v-model="allStates"
                        :indeterminate="someStatesChecked"
                        :binary="true"
                        input-id="lifecycle-state-all"
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
                        :binary="true"
                        :input-id="`lifecycle-state-${state.id}`"
                        @update:model-value="
                            (value) => setStateChecked(state.id, value)
                        "
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
