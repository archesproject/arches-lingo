<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Dialog from "primevue/dialog";

import BasicSearch from "@/arches_lingo/components/basic-search/BasicSearch.vue";

import {
    SEARCH_RESULTS_PER_PAGE,
    SEARCH_RESULT_ITEM_SIZE,
} from "@/arches_lingo/constants.ts";

const { $gettext } = useGettext();

const visible = ref(false);
const toggleModal = () => {
    visible.value = !visible.value;
};
</script>

<template>
    <Button
        class="basic-search-button"
        icon="pi pi-search"
        variant="text"
        :label="$gettext('Search')"
        @click="toggleModal"
    />

    <Dialog
        v-model:visible="visible"
        position="top"
        :header="$gettext('Search')"
        :dismissable-mask="true"
        :close-on-escape="true"
        :modal="true"
        :pt="{
            content: {
                style: {
                    padding: 0,
                    overflow: 'visible',
                },
            },
            root: {
                class: 'basic-search-dialog',
            },
        }"
        :show-header="false"
    >
        <div style="width: 80vw">
            <BasicSearch
                :search-results-per-page="SEARCH_RESULTS_PER_PAGE"
                :search-result-item-size="SEARCH_RESULT_ITEM_SIZE"
                :toggle-modal="toggleModal"
            />
        </div>
    </Dialog>
</template>

<!-- NOT scoped because dialog gets appended to <body> and is unreachable via scoped styles -->
<style>
.basic-search-button {
    color: var(--p-menubar-text-color) !important;
}

.basic-search-button:hover {
    background: var(--p-button-primary-hover-background) !important;
}

.basic-search-dialog {
    margin-top: 6rem !important;
    border-radius: 0 !important;
}

@media screen and (max-width: 960px) {
    .basic-search-dialog {
        margin-top: 1rem !important;
    }
}
</style>
