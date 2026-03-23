<script setup lang="ts">
import { useGettext } from "vue3-gettext";

import type { DashboardStats } from "@/arches_lingo/types/dashboard.ts";

const { $gettext } = useGettext();

defineProps<{
    stats: DashboardStats | null;
}>();
</script>

<template>
    <div
        v-if="stats"
        class="breakdowns-grid-container"
    >
        <div class="data-section-header">
            <h2>{{ $gettext("Label Metrics") }}</h2>
        </div>
        <div class="breakdowns-grid">
            <section
                v-if="
                    stats.concepts_by_type && stats.concepts_by_type.length > 0
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
                            item.count.toLocaleString()
                        }}</span>
                    </div>
                </div>
            </section>

            <section
                v-if="stats.labels_by_type && stats.labels_by_type.length > 0"
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
                            item.count.toLocaleString()
                        }}</span>
                    </div>
                </div>
            </section>

            <section
                v-if="
                    stats.labels_by_language &&
                    stats.labels_by_language.length > 0
                "
                class="dashboard-section"
            >
                <div class="section-header">
                    <h2>{{ $gettext("Labels by Language") }}</h2>
                </div>
                <div class="type-breakdown">
                    <div
                        v-for="item in stats.labels_by_language"
                        :key="item.code"
                        class="type-chip"
                    >
                        <span class="type-label">{{ item.language }}</span>
                        <span class="type-count">{{
                            item.count.toLocaleString()
                        }}</span>
                    </div>
                </div>
            </section>
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
</style>
