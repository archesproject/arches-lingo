<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useGettext } from "vue3-gettext";

import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Skeleton from "primevue/skeleton";
import Tag from "primevue/tag";

import type { DashboardStats } from "@/arches_lingo/types/dashboard.ts";

import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

const { $gettext } = useGettext();
const { selectedLanguage } = storeToRefs(useLanguageStore());

defineProps<{
    stats: DashboardStats | null;
    isLoading: boolean;
}>();
</script>

<template>
    <div class="breakdowns-grid-container">
        <div class="data-section-header">
            <h2>{{ $gettext("Label Metrics") }}</h2>
        </div>
        <div class="breakdowns-grid">
            <template v-if="isLoading">
                <section class="dashboard-section">
                    <div class="section-header">
                        <Skeleton
                            width="9rem"
                            height="0.75rem"
                        />
                    </div>
                    <div class="type-breakdown">
                        <Skeleton
                            v-for="n in 3"
                            :key="n"
                            width="9rem"
                            height="5.5rem"
                        />
                    </div>
                </section>
                <section class="dashboard-section">
                    <div class="section-header">
                        <Skeleton
                            width="9rem"
                            height="0.75rem"
                        />
                    </div>
                    <div class="type-breakdown">
                        <Skeleton
                            v-for="n in 4"
                            :key="n"
                            width="9rem"
                            height="5.5rem"
                        />
                    </div>
                </section>
                <section class="dashboard-section language-section">
                    <div class="section-header">
                        <Skeleton
                            width="12rem"
                            height="1rem"
                        />
                    </div>
                    <Skeleton
                        v-for="n in 6"
                        :key="n"
                        style="margin-bottom: 0.5rem"
                        height="2.25rem"
                    />
                </section>
            </template>
            <template v-else-if="stats">
                <section
                    v-if="
                        stats.concepts_by_type &&
                        stats.concepts_by_type.length > 0
                    "
                    class="dashboard-section"
                >
                    <div class="section-header">
                        <h2>{{ $gettext("Concepts by Type") }}</h2>
                    </div>
                    <div class="type-breakdown">
                        <div
                            v-for="item in stats.concepts_by_type"
                            :key="item.uri ?? 'untyped'"
                            class="type-chip"
                        >
                            <span class="type-label">{{ item.label }}</span>
                            <span class="type-count">{{
                                item.count.toLocaleString(selectedLanguage.code)
                            }}</span>
                        </div>
                    </div>
                </section>

                <section
                    v-if="
                        stats.labels_by_type && stats.labels_by_type.length > 0
                    "
                    class="dashboard-section"
                >
                    <div class="section-header">
                        <h2>{{ $gettext("Labels by Type") }}</h2>
                    </div>
                    <div class="type-breakdown">
                        <div
                            v-for="item in stats.labels_by_type"
                            :key="item.uri"
                            class="type-chip"
                        >
                            <span class="type-label">{{ item.label }}</span>
                            <span class="type-count">{{
                                item.count.toLocaleString(selectedLanguage.code)
                            }}</span>
                        </div>
                    </div>
                </section>

                <section
                    v-if="
                        stats.labels_by_language &&
                        stats.labels_by_language.length > 0
                    "
                    class="dashboard-section language-section"
                >
                    <div class="section-header">
                        <h2>{{ $gettext("Labels by Language") }}</h2>
                    </div>
                    <DataTable
                        :value="stats.labels_by_language"
                        striped-rows
                        size="small"
                        scrollable
                        scroll-height="20rem"
                    >
                        <Column
                            field="language"
                            :header="$gettext('Language')"
                        />
                        <Column
                            :header="$gettext('Code')"
                            style="width: 16rem"
                        >
                            <template #body="slotProps">
                                <Tag
                                    :value="slotProps.data.code"
                                    severity="secondary"
                                />
                            </template>
                        </Column>
                        <Column
                            :header="$gettext('Labels')"
                            style="width: 6rem"
                        >
                            <template #body="slotProps">
                                {{
                                    slotProps.data.count.toLocaleString(
                                        selectedLanguage.code,
                                    )
                                }}
                            </template>
                        </Column>
                    </DataTable>
                </section>
            </template>
        </div>
    </div>
</template>

<style scoped>
.breakdowns-grid-container {
    display: flex;
    flex-direction: column;
    padding: 1rem 1rem 0 1rem;
}

.data-section-header h2 {
    margin: 0;
    font-size: var(--p-lingo-font-size-medium);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-500);
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
    padding-bottom: 0.5rem;
}

.breakdowns-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.5rem 2rem;
    padding-bottom: 1rem;
}

.dashboard-section {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    background: var(--p-content-background);
    padding: 0.5rem 0;
}

.section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 0.25rem;
}

.section-header h2 {
    margin: 0;
    font-size: var(--p-lingo-font-size-xsmall);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-400);
}

.type-breakdown {
    display: flex;
    flex-wrap: wrap;
    gap: 0.375rem;
}

.type-chip {
    display: flex;
    flex-direction: column-reverse;
    align-items: center;
    gap: 0.375rem;
    padding: 0.75rem 1.625rem;
    border-radius: 0.25rem;
    background: var(--p-highlight-background);
    border: 0.125rem solid var(--p-highlight-focus-background);
    font-size: var(--p-lingo-font-size-smallnormal);
    text-transform: capitalize;
    min-width: 9rem;
}

.type-label {
    color: var(--p-neutral-400);
}

.type-count {
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-text-color);
}

@media (max-width: 960px) {
    .breakdowns-grid {
        grid-template-columns: 1fr;
    }
}

.language-section {
    grid-column: 1 / -1;
    gap: 0.75rem;
}

.language-section .section-header {
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
    padding-bottom: 0.5rem;
}

.language-section .section-header h2 {
    font-size: var(--p-lingo-font-size-medium);
    color: var(--p-neutral-500);
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

:deep(.p-tag) {
    border-radius: 0.125rem;
    font-size: var(--p-lingo-font-size-xsmall);
}
</style>
