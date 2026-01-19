<script setup lang="ts">
import { useGettext } from "vue3-gettext";
import RadioButton from "primevue/radiobutton";

const { $gettext } = useGettext();

const ORDER_MODE_UNSORTED = "unsorted";
const ORDER_MODE_ALPHABETICAL = "alphabetical";
const ORDER_MODE_REVERSE_ALPHABETICAL = "reverse-alphabetical";

const sortOptions = [
    { value: ORDER_MODE_UNSORTED, label: $gettext("Best Match") },
    { value: ORDER_MODE_ALPHABETICAL, label: $gettext("A to Z") },
    { value: ORDER_MODE_REVERSE_ALPHABETICAL, label: $gettext("Z to A") },
];

const { orderMode } = defineProps<{
    orderMode: string;
}>();

const emit = defineEmits<{
    (event: "update:orderMode", value: string): void;
}>();

function onOrderModeChange(newOrderMode: string) {
    emit("update:orderMode", newOrderMode);
}
</script>

<template>
    <div class="sort-and-filter-controls">
        <div class="sort-container">
            <div class="label">{{ $gettext("Sorting:") }}</div>

            <div
                v-for="(sortOption, index) in sortOptions"
                :key="sortOption.value"
                class="query-sort-preference"
            >
                <RadioButton
                    :model-value="orderMode"
                    :input-id="`querySortPreference${index + 1}`"
                    name="querySortPreference"
                    :value="sortOption.value"
                    @update:model-value="onOrderModeChange"
                />
                <label :for="`querySortPreference${index + 1}`">
                    {{ sortOption.label }}
                </label>
            </div>
        </div>
    </div>
</template>

<style scoped>
.sort-and-filter-controls {
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: flex-start;
    padding: 1rem;
    background-color: var(--p-sort-and-filter-controls-background);
    border-top: 0.0625rem solid var(--p-sort-and-filter-controls-border);
    gap: 1rem;
    flex-wrap: wrap;
}

.sort-container,
.filter-container {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.label {
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-button-text-secondary-color);
}

.query-sort-preference,
.query-filter {
    display: flex;
    align-items: center;
}

.query-sort-preference label,
.query-filter label {
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-button-text-secondary-color);
}

label {
    margin-left: 0.25rem;
    cursor: pointer;
}

:deep(.p-radiobutton-box),
:deep(.p-checkbox-box) {
    background-color: var(--p-checkbox-background);
    border: 0.0625rem solid;
    border-color: var(--p-button-text-secondary-color);
}

@media screen and (max-width: 960px) {
    .sort-and-filter-controls {
        flex-direction: column;
        align-items: flex-start;
    }

    .sort-container,
    .filter-container {
        width: 100%;
    }

    .label {
        width: 100%;
        margin-bottom: 0.5rem;
    }
}
</style>
