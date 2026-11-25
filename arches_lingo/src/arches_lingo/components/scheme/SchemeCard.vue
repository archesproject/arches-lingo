<script setup lang="ts">
import { computed, ref } from "vue";
import { storeToRefs } from "pinia";
import { NEW } from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import Card from "openvue/card";
import Button from "openvue/button";

import ImportThesauri from "@/arches_lingo/components/scheme/ImportThesauri.vue";

import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { getStatementText } from "@/arches_lingo/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

import type { Scheme, SchemeStatement } from "@/arches_lingo/types";

const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

const { scheme, statements } = defineProps<{
    scheme: Scheme;
    statements?: SchemeStatement[];
}>();
const emit = defineEmits<{
    (e: "imported"): void;
}>();

const schemeURL = {
    name: routeNames.scheme,
    params: { id: scheme.id },
};

const schemeName = computed(() =>
    getItemLabel(
        scheme,
        selectedLanguage.value.code,
        systemLanguage.value.code,
    ),
);

const schemeDescription = computed(() => {
    if (!statements?.length) return "";
    return getStatementText(
        statements,
        selectedLanguage.value.code,
        systemLanguage.value.code,
    );
});

const showImportDialog = ref(false);
const importDialogKey = ref(0);

function openImportDialog() {
    importDialogKey.value++;
    showImportDialog.value = true;
}

function onImport() {
    showImportDialog.value = false;
    emit("imported");
}
</script>

<template>
    <Card :class="scheme.id === NEW ? 'new-scheme' : ''">
        <template #title>
            <h2
                v-if="scheme.id === NEW"
                class="scheme-card-title"
            >
                <RouterLink
                    :to="schemeURL"
                    class="scheme-card-link"
                >
                    {{ $gettext("New Scheme") }}
                </RouterLink>
            </h2>
            <h2
                v-else
                class="scheme-card scheme-card-title"
            >
                <RouterLink
                    :to="schemeURL"
                    class="scheme-card-link"
                >
                    {{ schemeName.value }}
                </RouterLink>
            </h2>
        </template>
        <template #content>
            <div v-if="scheme.id === NEW">
                <div class="scheme-circle">
                    <i class="pi pi-share-alt new-scheme-icon"></i>
                </div>
                <div>
                    <span>{{
                        $gettext(
                            "Add a new thesaurus, manage concept hierarchies",
                        )
                    }}</span>
                </div>
            </div>
            <span v-else>{{ schemeDescription }}</span>
        </template>
        <template
            v-if="scheme.id === NEW"
            #footer
        >
            <Button
                :label="$gettext('Import Thesauri')"
                type="button"
                outlined
                class="import-button"
                @click="openImportDialog"
            />
        </template>
    </Card>
    <ImportThesauri
        v-if="showImportDialog"
        :key="importDialogKey"
        @imported="onImport"
    />
</template>

<style scoped>
.p-card.new-scheme {
    color: var(--p-lingo-new-scheme-card-color);
    background: var(--p-lingo-new-scheme-card-background);
    border: 0.0625rem solid var(--p-lingo-new-scheme-card-border-color);
}

.scheme-card-link {
    color: inherit;
    text-decoration: none;
}

.scheme-card-link::after {
    content: "";
    position: absolute;
    inset: 0;
}

/* Draw the link's focus ring around the whole card, as before. */
.scheme-card-link:focus-visible {
    outline: none;
}

.p-card:has(.scheme-card-link:focus-visible) {
    outline: var(--p-lingo-scheme-card-focus-outline);
    outline-offset: var(--p-lingo-scheme-card-focus-outline-offset);
}

.import-button {
    position: relative;
    z-index: 1;
}

.import-button:focus-visible {
    outline: 0.125rem solid
        var(--p-lingo-new-scheme-card-button-focus-ring-color);
    outline-offset: -0.25rem;
    box-shadow: none;
}

.scheme-card-title {
    margin: 0;
    font-size: inherit;
    font-weight: inherit;
}

.p-card {
    position: relative;
    background-color: var(--p-button-primary-background);
    border: 0.0625rem solid var(--p-header-toolbar-border);
    color: var(--p-button-primary-color);
    width: 15rem;
    height: 15rem;
    margin: 0.25rem;
    border-radius: 0.125rem;
}

:deep(.p-card-body) {
    flex-grow: 1;
    text-align: center;
    overflow: hidden;
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
}

.new-scheme > :deep(.p-card-body) {
    margin-bottom: 0;
    padding-bottom: 0;
    gap: 0;

    :deep(.p-card-footer) {
        margin-top: 1rem;
        display: flex;
    }
}

.new-scheme :deep(.p-button) {
    border-radius: 0;
    flex-grow: 1;
    font-size: var(--p-lingo-font-size-xsmall);
    color: var(--p-lingo-new-scheme-card-button-color);
    background: var(--p-lingo-new-scheme-card-button-background);
    border-color: var(--p-lingo-new-scheme-card-button-border-color);
}

.new-scheme :deep(.p-button:hover) {
    color: var(--p-lingo-new-scheme-card-button-hover-color);
    background: var(--p-lingo-new-scheme-card-button-hover-background);
}

:deep(.p-card-content) {
    overflow: hidden;
    text-overflow: ellipsis;
}

:deep(.p-card-content),
:deep(.p-card-footer) {
    font-size: var(--p-lingo-font-size-xsmall);
}

.scheme-circle {
    display: inline-block;
    text-align: center;
    padding: 1.25rem;
    margin: 0.75rem;
    border-radius: 50%;
    background: var(--p-lingo-new-scheme-card-circle-background);
    border: 0.0625rem solid var(--p-lingo-new-scheme-card-circle-border-color);
}

.new-scheme-icon {
    font-size: var(--p-lingo-font-size-xxlarge);
}
</style>
