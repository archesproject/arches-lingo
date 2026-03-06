<script setup lang="ts">
import { computed, ref } from "vue";
import { storeToRefs } from "pinia";
import { NEW } from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import Card from "primevue/card";
import Button from "primevue/button";

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
    <RouterLink :to="schemeURL">
        <Card :class="scheme.id === NEW ? 'new-scheme' : ''">
            <template #title>
                <div v-if="scheme.id === NEW">
                    {{ $gettext("New Scheme") }}
                </div>
                <div
                    v-else
                    class="scheme-card"
                >
                    {{ schemeName.value }}
                </div>
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
                    @click.stop.prevent="openImportDialog"
                />
            </template>
        </Card>
    </RouterLink>
    <ImportThesauri
        v-if="showImportDialog"
        :key="importDialogKey"
        @imported="onImport"
    />
</template>

<style scoped>
ul:first-child li:first-child .p-card {
    color: var(--p-button-contrast-color);
    background: var(--p-arches-blue);
    border: 0.0625rem solid var(--p-surface-900);
}

ul:first-child li:first-child .p-card .scheme-circle {
    background: var(--p-blue-600);
}

a {
    text-decoration: none;
}

:deep(.p-card) {
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
    color: var(--p-button-contrast-color);
    background: var(--p-button-primary-hover-background);
}

.new-scheme :deep(.p-button:hover) {
    background: var(--p-primary-active-color);
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
    background: var(--p-surface-400);
    border: 0.0625rem solid var(--p-surface-900);
}

.new-scheme-icon {
    font-size: var(--p-lingo-font-size-xxlarge);
}
</style>
