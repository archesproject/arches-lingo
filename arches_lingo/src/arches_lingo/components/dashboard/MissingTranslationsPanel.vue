<script setup lang="ts">
import { useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";

import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Paginator from "primevue/paginator";
import Select from "primevue/select";
import Skeleton from "primevue/skeleton";
import { storeToRefs } from "pinia";

import { routeNames } from "@/arches_lingo/routes.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

import type { Language } from "@/arches_component_lab/types.ts";
import type { MissingTranslationsResponse } from "@/arches_lingo/types/dashboard.ts";
import type { SearchResultItem } from "@/arches_lingo/types.ts";

const props = defineProps<{
    languages: Language[];
    translationLanguage: Language | null;
    isLoading: boolean;
    missingTranslations: MissingTranslationsResponse | null;
    missingPage: number;
}>();

const emit = defineEmits<{
    "update:translationLanguage": [value: Language | null];
    pageChange: [event: { first: number; rows: number }];
}>();

const router = useRouter();
const { $gettext } = useGettext();

const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

function navigateToConcept(conceptId: string) {
    router.push({ name: routeNames.concept, params: { id: conceptId } });
}

function getConceptLabel(concept: SearchResultItem): string {
    return (
        getItemLabel(
            concept,
            selectedLanguage.value.code,
            systemLanguage.value.code,
        ).value ||
        concept.labels[0]?.value ||
        ""
    );
}

function getConceptScheme(concept: SearchResultItem): string {
    const topParents = concept.parents?.[0];
    if (topParents && topParents.length > 0) {
        const scheme = topParents[0];
        return scheme.labels[0]?.value || "";
    }
    return "";
}
</script>

<template>
    <section class="dashboard-section">
        <div class="section-header">
            <div class="section-header-left">
                <h2>
                    {{ $gettext("Missing Translations") }}
                </h2>
                <span
                    v-if="
                        missingTranslations &&
                        missingTranslations.total_results > 0
                    "
                    class="count-badge"
                >
                    {{ missingTranslations.total_results.toLocaleString() }}
                </span>
            </div>
            <div class="filter-group">
                <label
                    for="language-filter"
                    class="filter-label"
                >
                    {{ $gettext("Language") }}:
                </label>
                <Select
                    id="language-filter"
                    :model-value="props.translationLanguage"
                    :options="props.languages"
                    option-label="name"
                    :placeholder="$gettext('Select a language')"
                    class="language-select"
                    @update:model-value="
                        emit('update:translationLanguage', $event)
                    "
                />
            </div>
        </div>

        <div v-if="!props.translationLanguage">
            <p class="hint-text">
                {{
                    $gettext(
                        "Select a language to see concepts missing translations.",
                    )
                }}
            </p>
        </div>
        <div v-else-if="isLoading">
            <Skeleton
                v-for="index in 5"
                :key="index"
                style="margin-bottom: 0.5rem"
                height="2.25rem"
            />
        </div>
        <template v-else>
            <DataTable
                :value="missingTranslations?.data ?? []"
                striped-rows
                size="small"
                class="missing-table"
            >
                <template #empty>
                    <div class="empty-state">
                        <i
                            class="pi pi-check-circle empty-icon empty-icon--success"
                        />
                        <span>{{
                            $gettext(
                                "All concepts have a preferred label in this language.",
                            )
                        }}</span>
                    </div>
                </template>
                <Column :header="$gettext('Concept')">
                    <template #body="slotProps">
                        <a
                            class="resource-link"
                            href="#"
                            @click.prevent="
                                navigateToConcept(slotProps.data.id)
                            "
                        >
                            {{ getConceptLabel(slotProps.data) }}
                        </a>
                    </template>
                </Column>
                <Column :header="$gettext('Scheme')">
                    <template #body="slotProps">
                        {{ getConceptScheme(slotProps.data) }}
                    </template>
                </Column>
            </DataTable>
            <Paginator
                v-if="(missingTranslations?.total_results ?? 0) > 0"
                :rows="missingTranslations?.results_per_page ?? 25"
                :total-records="missingTranslations?.total_results ?? 0"
                :first="
                    missingPage * (missingTranslations?.results_per_page ?? 25)
                "
                @page="emit('pageChange', $event)"
            />
        </template>
    </section>
</template>

<style scoped>
.dashboard-section {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    background: var(--p-content-background);
    border: 0.0625rem solid var(--p-header-toolbar-border);
    border-radius: 0.125rem;
    padding: 1rem;
}

.section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
    padding-bottom: 0.5rem;
}

.section-header h2 {
    margin: 0;
    font-size: var(--p-lingo-font-size-medium);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-500);
}

.section-header-left {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.count-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: var(--p-primary-100);
    color: var(--p-primary-700);
    font-size: var(--p-lingo-font-size-xsmall);
    font-weight: var(--p-lingo-font-weight-normal);
    padding: 0.125rem 0.5rem;
    border-radius: 0.125rem;
    min-width: 1.5rem;
}

.filter-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.filter-label {
    font-size: var(--p-lingo-font-size-small);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-400);
    white-space: nowrap;
}

.language-select {
    min-width: 14rem;
    border-radius: 0.125rem;
}

.hint-text {
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-inputtext-placeholder-color);
    margin: 0;
}

.empty-state {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--p-inputtext-placeholder-color);
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-light);
    padding: 0.25rem 0;
}

.empty-icon {
    font-size: 1rem;
    color: var(--p-neutral-300);
}

.empty-icon--success {
    color: var(--p-green-500);
}

.resource-link {
    color: var(--p-primary-500);
    text-decoration: none;
    font-size: var(--p-lingo-font-size-smallnormal);
}

.resource-link:hover {
    text-decoration: underline;
}

:deep(.p-datatable-tbody > tr > td) {
    font-size: var(--p-lingo-font-size-smallnormal);
    padding: 0.4rem 0.75rem;
}

:deep(.p-datatable-column-title) {
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-500);
    font-size: var(--p-lingo-font-size-small);
}

@media (max-width: 960px) {
    .section-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.5rem;
    }
}
</style>
