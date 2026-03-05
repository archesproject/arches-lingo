<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import MultiSelect from "primevue/multiselect";
import Skeleton from "primevue/skeleton";

import { fetchLanguages } from "@/arches_component_lab/widgets/api.ts";
import {
    fetchDashboardStats,
    fetchLingoResources,
    fetchMissingTranslations,
} from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";

import BreakdownsGrid from "@/arches_lingo/components/dashboard/BreakdownsGrid.vue";
import DashboardStatCards from "@/arches_lingo/components/dashboard/DashboardStatCards.vue";
import MissingTranslationsPanel from "@/arches_lingo/components/dashboard/MissingTranslationsPanel.vue";
import RecentActivityTable from "@/arches_lingo/components/dashboard/RecentActivityTable.vue";

import type { Language } from "@/arches_component_lab/types.ts";
import type {
    DashboardStats,
    MissingTranslationsResponse,
} from "@/arches_lingo/types/dashboard.ts";
import type { ActivityPeriod } from "@/arches_lingo/components/dashboard/RecentActivityTable.vue";
import type { ResourceInstanceResult } from "@/arches_lingo/types.ts";

const toast = useToast();
const { $gettext } = useGettext();

const schemes = ref<ResourceInstanceResult[]>([]);
const selectedSchemeIds = ref<string[]>([]);

const isStatsLoading = ref(true);
const stats = ref<DashboardStats | null>(null);

const ACTIVITY_PERIODS: ActivityPeriod[] = [
    { label: $gettext("Last 24 hours"), days: 1 },
    { label: $gettext("Last 7 days"), days: 7 },
    { label: $gettext("Last 30 days"), days: 30 },
    { label: $gettext("Last 90 days"), days: 90 },
    { label: $gettext("All time"), days: 0 },
];
const selectedActivityPeriod = ref<ActivityPeriod>(ACTIVITY_PERIODS[1]);

const languages = ref<Language[]>([]);
const selectedLanguage = ref<Language | null>(null);
const isMissingLoading = ref(false);
const missingTranslations = ref<MissingTranslationsResponse | null>(null);
const missingPage = ref(0);

async function loadSchemes() {
    try {
        const data = await fetchLingoResources("scheme");
        schemes.value = data;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch schemes"),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

async function loadLanguages() {
    try {
        const response = await fetchLanguages();
        languages.value = (response.languages ?? response) as Language[];
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch languages"),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}

async function loadStats() {
    isStatsLoading.value = true;
    try {
        stats.value = await fetchDashboardStats(
            selectedSchemeIds.value.length
                ? selectedSchemeIds.value
                : undefined,
            selectedActivityPeriod.value.days,
        );
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch dashboard data"),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
    isStatsLoading.value = false;
}

async function loadMissingTranslations() {
    if (!selectedLanguage.value) return;
    isMissingLoading.value = true;
    try {
        missingTranslations.value = await fetchMissingTranslations(
            selectedLanguage.value.code,
            selectedSchemeIds.value.length
                ? selectedSchemeIds.value
                : undefined,
            missingPage.value + 1,
        );
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch missing translations"),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
    isMissingLoading.value = false;
}

const greeting = computed(() => {
    const name = stats.value?.user_display_name;
    if (name) {
        return $gettext("Welcome, %{name}", { name });
    }
    return $gettext("Welcome");
});

function onPageChange(event: { first: number; rows: number }) {
    missingPage.value = event.first / event.rows;
    loadMissingTranslations();
}

watch([selectedSchemeIds, selectedActivityPeriod], () => {
    missingPage.value = 0;
    loadStats();
    if (selectedLanguage.value) {
        loadMissingTranslations();
    }
});

watch(selectedLanguage, () => {
    missingPage.value = 0;
    loadMissingTranslations();
});

onMounted(async () => {
    await Promise.all([loadSchemes(), loadLanguages(), loadStats()]);
});
</script>

<template>
    <div class="dashboard">
        <div class="dashboard-header">
            <h1 class="welcome-heading">
                <Skeleton
                    v-if="isStatsLoading"
                    height="2rem"
                    width="16rem"
                />
                <template v-else>{{ greeting }}</template>
            </h1>
            <div class="dashboard-filters">
                <label
                    for="scheme-filter"
                    class="filter-label"
                >
                    {{ $gettext("Schemes") }}:
                </label>
                <MultiSelect
                    id="scheme-filter"
                    v-model="selectedSchemeIds"
                    :options="schemes"
                    option-label="name"
                    option-value="resourceinstanceid"
                    :placeholder="$gettext('All schemes')"
                    :max-selected-labels="2"
                    :selected-items-label="
                        $gettext('%{count} schemes selected', {
                            count: String(selectedSchemeIds.length),
                        })
                    "
                    display="chip"
                    filter
                    class="scheme-select"
                >
                    <template #option="slotProps">
                        {{
                            slotProps.option.descriptors?.en?.name ||
                            slotProps.option.name ||
                            $gettext("Unnamed scheme")
                        }}
                    </template>
                </MultiSelect>
            </div>
        </div>

        <DashboardStatCards
            :stats="stats"
            :is-loading="isStatsLoading"
        />

        <BreakdownsGrid
            v-if="!isStatsLoading"
            :stats="stats"
        />

        <RecentActivityTable
            v-model:selected-activity-period="selectedActivityPeriod"
            :stats="stats"
            :is-loading="isStatsLoading"
            :activity-periods="ACTIVITY_PERIODS"
        />

        <MissingTranslationsPanel
            v-model:selected-language="selectedLanguage"
            :languages="languages"
            :is-loading="isMissingLoading"
            :missing-translations="missingTranslations"
            :missing-page="missingPage"
            @page-change="onPageChange"
        />
    </div>
</template>

<style scoped>
.dashboard {
    padding: 1.5rem;
    height: 100%;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
}

.dashboard-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.75rem;
}

.welcome-heading {
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
    margin: 0;
    color: var(--p-text-color);
}

.dashboard-filters {
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

.scheme-select {
    min-width: 14rem;
    border-radius: 0.125rem;
}

@media (max-width: 960px) {
    .dashboard-header {
        flex-direction: column;
        align-items: flex-start;
    }
}
</style>
