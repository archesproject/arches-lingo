<script setup lang="ts">
import { useGettext } from "vue3-gettext";
import Skeleton from "primevue/skeleton";

import type { DashboardStats } from "@/arches_lingo/types/dashboard.ts";

const { $gettext } = useGettext();

defineProps<{
    stats: DashboardStats | null;
    isLoading: boolean;
}>();
</script>

<template>
    <div class="stats-row">
        <div class="stat-card">
            <div class="stat-card-title">
                <i class="pi pi-folder stat-icon" />
                {{ $gettext("Schemes") }}
            </div>
            <Skeleton
                v-if="isLoading"
                height="2.5rem"
                width="5rem"
            />
            <div
                v-else
                class="stat-count"
            >
                {{ stats?.scheme_count?.toLocaleString() ?? "—" }}
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-card-title">
                <i class="pi pi-lightbulb stat-icon" />
                {{ $gettext("Concepts") }}
            </div>
            <Skeleton
                v-if="isLoading"
                height="2.5rem"
                width="5rem"
            />
            <div
                v-else
                class="stat-count"
            >
                {{ stats?.concept_count?.toLocaleString() ?? "—" }}
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-card-title">
                <i class="pi pi-tag stat-icon" />
                {{ $gettext("Labels") }}
            </div>
            <Skeleton
                v-if="isLoading"
                height="2.5rem"
                width="5rem"
            />
            <div
                v-else
                class="stat-count"
            >
                {{ stats?.label_count?.toLocaleString() ?? "—" }}
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-card-title">
                <i class="pi pi-chart-bar stat-icon" />
                {{ $gettext("Labels / Concept") }}
            </div>
            <Skeleton
                v-if="isLoading"
                height="2.5rem"
                width="5rem"
            />
            <div
                v-else
                class="stat-count"
            >
                {{ stats?.labels_per_concept ?? "—" }}
            </div>
        </div>
    </div>
</template>

<style scoped>
.stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.75rem;
}

.stat-card {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 1rem;
    border: 0.0625rem solid var(--p-header-toolbar-border);
    border-radius: 0.125rem;
    background: var(--p-content-background);
}

.stat-card-title {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: var(--p-lingo-font-size-xsmall);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-400);
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.stat-icon {
    font-size: 0.75rem;
    color: var(--p-primary-500);
}

.stat-count {
    font-size: 2rem;
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-text-color);
    line-height: 1;
}

@media (max-width: 960px) {
    .stats-row {
        grid-template-columns: repeat(2, 1fr);
    }
}
</style>
