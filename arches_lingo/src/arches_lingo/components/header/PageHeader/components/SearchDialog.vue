<script setup lang="ts">
import { ref, useTemplateRef } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Dialog from "primevue/dialog";

import BasicSearch from "@/arches_lingo/components/basic-search/BasicSearch.vue";

import { SEARCH_RESULTS_PER_PAGE } from "@/arches_lingo/constants.ts";

import type { ComponentPublicInstance } from "vue";

const { $gettext } = useGettext();

const searchButton = useTemplateRef<ComponentPublicInstance>("searchButton");
const visible = ref(false);
let wasClosedBySelectingResult = false;

const toggleModal = () => {
    wasClosedBySelectingResult = false;
    visible.value = !visible.value;
};

function onSearchResultSelect() {
    wasClosedBySelectingResult = true;
    visible.value = false;
}

function onSearchDialogAfterHide() {
    if (!wasClosedBySelectingResult) {
        (searchButton.value?.$el as HTMLElement | undefined)?.focus();
    }
    wasClosedBySelectingResult = false;
}
</script>

<template>
    <Button
        ref="searchButton"
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
                'aria-label': $gettext('Search'),
            },
        }"
        :show-header="false"
        @after-hide="onSearchDialogAfterHide"
    >
        <div style="width: 80vw">
            <BasicSearch
                :search-results-per-page="SEARCH_RESULTS_PER_PAGE"
                @select="onSearchResultSelect"
            />
        </div>
    </Dialog>
</template>

<!-- NOT scoped because dialog gets appended to <body> and is unreachable via scoped styles -->
<style>
.basic-search-button {
    color: inherit !important;
    border-radius: 0 !important;
    padding: var(--p-button-padding-x) var(--p-button-padding-y) !important;
    font-size: 0.875rem !important;
    height: 3rem;
}

.basic-search-button:hover {
    background: var(--p-lingo-navigation-bar-hover-background) !important;
}

.basic-search-dialog {
    margin-top: 6rem !important;
    border-radius: 0.25rem !important;
    border: 0.125rem solid var(--p-dialog-color) !important;
}

@media screen and (max-width: 960px) {
    .basic-search-dialog {
        margin-top: 1rem !important;
    }
}
</style>
