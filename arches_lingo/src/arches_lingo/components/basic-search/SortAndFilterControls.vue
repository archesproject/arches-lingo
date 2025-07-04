<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Checkbox from "primevue/checkbox";
import RadioButton from "primevue/radiobutton";

const { $gettext } = useGettext();

const filters = [
    { value: "Concepts", label: $gettext("Concepts") },
    { value: "Places", label: $gettext("Places") },
    { value: "People", label: $gettext("People") },
    { value: "Groups", label: $gettext("Groups") },
    { value: "Periods", label: $gettext("Periods") },
];
const queryFilters = ref([]);

const sortOptions = [
    { value: "Unsorted", label: $gettext("Unsorted") },
    { value: "A to Z", label: $gettext("A to Z") },
    { value: "Z to A", label: $gettext("Z to A") },
];
const querySortPreference = ref();
</script>

<template>
    <div class="sort-and-filter-controls">
        <div class="sort-container">
            <div class="label">{{ $gettext("Sorting:") }}</div>

            <div
                v-for="(sortOption, index) in sortOptions"
                :key="index"
                class="query-sort-preference"
            >
                <RadioButton
                    v-model="querySortPreference"
                    :input-id="`querySortPreference${index + 1}`"
                    :name="`querySortPreference${index + 1}`"
                    :value="sortOption.value"
                />
                <label :for="`querySortPreference${index + 1}`">{{
                    sortOption.label
                }}</label>
            </div>
        </div>

        <div class="filter-container">
            <div class="label">{{ $gettext("Include:") }}</div>

            <div
                v-for="(filter, index) in filters"
                :key="index"
                class="query-filter"
            >
                <Checkbox
                    v-model="queryFilters"
                    :input-id="`queryFilter${index + 1}`"
                    :name="`queryFilter${index + 1}`"
                    :value="filter.value"
                />
                <label :for="`queryFilter${index + 1}`">{{
                    filter.label
                }}</label>
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
    border-top: 0.06rem solid var(--p-sort-and-filter-controls-border);
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
    border: 0.06rem solid;
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
