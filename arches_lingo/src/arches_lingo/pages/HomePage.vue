<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Card from "primevue/card";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Paginator from "primevue/paginator";
import Select from "primevue/select";
import Skeleton from "primevue/skeleton";

import { fetchLanguages } from "@/arches_component_lab/widgets/api.ts";
import {
    fetchDashboardStats,
    fetchLingoResources,
    fetchMissingTranslations,
} from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";

import type { Language } from "@/arches_component_lab/types.ts";
import type {
    DashboardStats,
    MissingTranslationsResponse,
    ResourceInstanceResult,
    SearchResultItem,
} from "@/arches_lingo/types.ts";

const toast = useToast();
const router = useRouter();
const { $gettext } = useGettext();

// --- Scheme filter ---
const schemes = ref<ResourceInstanceResult[]>([]);
const selectedSchemeId = ref<string | undefined>(undefined);

// --- Dashboard stats ---
const isStatsLoading = ref(true);
const stats = ref<DashboardStats | null>(null);

// --- Missing translations ---
const languages = ref<Language[]>([]);
const selectedLanguage = ref<Language | null>(null);
const isMissingLoading = ref(false);
const missingTranslations = ref<MissingTranslationsResponse | null>(null);
const missingPage = ref(0); // PrimeVue Paginator uses 0-based first

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
        stats.value = await fetchDashboardStats(selectedSchemeId.value);
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
            selectedSchemeId.value,
            missingPage.value + 1, // API is 1-based
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

function getConceptLabel(concept: SearchResultItem): string {
    return (
        getItemLabel(concept, "en", "en").value ||
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

function formatTimestamp(timestamp: string | null): string {
    if (!timestamp) return "";
    return new Date(timestamp).toLocaleString();
}

function navigateToConcept(conceptId: string) {
    router.push({ name: routeNames.concept, params: { id: conceptId } });
}

function navigateToScheme(schemeId: string) {
    router.push({ name: routeNames.scheme, params: { id: schemeId } });
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

watch(selectedSchemeId, () => {
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
        <!-- Welcome + Scheme filter -->
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
                    {{ $gettext("Scheme") }}:
                </label>
                <Select
                    id="scheme-filter"
                    v-model="selectedSchemeId"
                    :options="schemes"
                    option-label="name"
                    option-value="resourceinstanceid"
                    :placeholder="$gettext('All schemes')"
                    show-clear
                    class="scheme-select"
                >
                    <template #option="slotProps">
                        {{
                            slotProps.option.descriptors?.en?.name ||
                            slotProps.option.name ||
                            $gettext("Unnamed scheme")
                        }}
                    </template>
                    <template #value="slotProps">
                        <span v-if="slotProps.value">
                            {{
                                schemes.find(
                                    (s) =>
                                        s.resourceinstanceid ===
                                        slotProps.value,
                                )?.descriptors?.en?.name ||
                                $gettext("Selected scheme")
                            }}
                        </span>
                        <span v-else>{{ $gettext("All schemes") }}</span>
                    </template>
                </Select>
            </div>
        </div>

        <!-- Stat cards -->
        <div class="stats-row">
            <Card class="stat-card">
                <template #title>
                    <span class="stat-title">
                        <i class="pi pi-folder stat-icon" />
                        {{ $gettext("Schemes") }}
                    </span>
                </template>
                <template #content>
                    <Skeleton
                        v-if="isStatsLoading"
                        height="3rem"
                        width="6rem"
                    />
                    <div
                        v-else
                        class="stat-count"
                    >
                        {{ stats?.scheme_count?.toLocaleString() ?? "—" }}
                    </div>
                </template>
            </Card>
            <Card class="stat-card">
                <template #title>
                    <span class="stat-title">
                        <i class="pi pi-lightbulb stat-icon" />
                        {{ $gettext("Concepts") }}
                    </span>
                </template>
                <template #content>
                    <Skeleton
                        v-if="isStatsLoading"
                        height="3rem"
                        width="6rem"
                    />
                    <div
                        v-else
                        class="stat-count"
                    >
                        {{ stats?.concept_count?.toLocaleString() ?? "—" }}
                    </div>
                </template>
            </Card>
        </div>

        <!-- Concepts by Type -->
        <section
            v-if="
                !isStatsLoading &&
                stats?.concepts_by_type &&
                stats.concepts_by_type.length > 0
            "
            class="dashboard-section"
        >
            <h2 class="section-title">
                {{ $gettext("Concepts by Type") }}
            </h2>
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

        <!-- Recent Activity -->
        <section class="dashboard-section">
            <h2 class="section-title">{{ $gettext("Recent Activity") }}</h2>
            <div v-if="isStatsLoading">
                <Skeleton
                    v-for="n in 5"
                    :key="n"
                    style="margin-bottom: 0.5rem"
                    height="2rem"
                />
            </div>
            <DataTable
                v-else
                :value="stats?.recent_activity ?? []"
                striped-rows
                size="small"
                class="activity-table"
            >
                <template #empty>
                    <span class="no-data">{{
                        $gettext("No recent activity")
                    }}</span>
                </template>
                <Column
                    :header="$gettext('Date / Time')"
                    style="width: 12rem"
                >
                    <template #body="slotProps">
                        {{ formatTimestamp(slotProps.data.timestamp) }}
                    </template>
                </Column>
                <Column
                    field="edittype_label"
                    :header="$gettext('Action')"
                    style="width: 10rem"
                />
                <Column :header="$gettext('Resource')">
                    <template #body="slotProps">
                        <a
                            class="resource-link"
                            href="#"
                            @click.prevent="
                                slotProps.data.resource_type === 'scheme'
                                    ? navigateToScheme(
                                          slotProps.data.resource_id,
                                      )
                                    : navigateToConcept(
                                          slotProps.data.resource_id,
                                      )
                            "
                        >
                            {{
                                slotProps.data.resource_name ||
                                slotProps.data.resource_id
                            }}
                        </a>
                    </template>
                </Column>
                <Column
                    :header="$gettext('Type')"
                    style="width: 7rem"
                >
                    <template #body="slotProps">
                        {{
                            slotProps.data.resource_type === "scheme"
                                ? $gettext("Scheme")
                                : $gettext("Concept")
                        }}
                    </template>
                </Column>
                <Column
                    :header="$gettext('User')"
                    style="width: 10rem"
                >
                    <template #body="slotProps">
                        {{
                            slotProps.data.user_firstname ||
                            slotProps.data.user_lastname
                                ? `${slotProps.data.user_firstname} ${slotProps.data.user_lastname}`.trim()
                                : slotProps.data.user_username
                        }}
                    </template>
                </Column>
            </DataTable>
        </section>

        <!-- Missing Translations -->
        <section class="dashboard-section">
            <h2 class="section-title">
                {{ $gettext("Missing Translations") }}
            </h2>
            <div class="missing-filters">
                <label
                    for="language-filter"
                    class="filter-label"
                >
                    {{ $gettext("Language") }}:
                </label>
                <Select
                    id="language-filter"
                    v-model="selectedLanguage"
                    :options="languages"
                    option-label="name"
                    :placeholder="$gettext('Select a language')"
                    class="language-select"
                />
            </div>

            <div v-if="!selectedLanguage">
                <p class="hint-text">
                    {{
                        $gettext(
                            "Select a language to see concepts missing translations.",
                        )
                    }}
                </p>
            </div>
            <div v-else-if="isMissingLoading">
                <Skeleton
                    v-for="n in 5"
                    :key="n"
                    style="margin-bottom: 0.5rem"
                    height="2rem"
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
                        <span class="no-data">
                            {{
                                $gettext(
                                    "All concepts have a preferred label in this language.",
                                )
                            }}
                        </span>
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
                        missingPage *
                        (missingTranslations?.results_per_page ?? 25)
                    "
                    @page="onPageChange"
                />
                <p
                    v-if="missingTranslations"
                    class="results-count"
                >
                    {{
                        $gettext(
                            "%{count} concept(s) missing a preferred label in %{lang}",
                            {
                                count: String(
                                    missingTranslations.total_results,
                                ),
                                lang: selectedLanguage?.name ?? "",
                            },
                        )
                    }}
                </p>
            </template>
        </section>
    </div>
</template>

<style scoped>
.dashboard {
    padding: 1.5rem;
    height: 100%;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.dashboard-header {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.welcome-heading {
    font-size: 1.5rem;
    font-weight: 400;
    margin: 0;
    color: var(--p-text-color);
}

.dashboard-filters {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.filter-label {
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-neutral-400);
    white-space: nowrap;
}

.scheme-select,
.language-select {
    min-width: 14rem;
}

.stats-row {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
}

.stat-card {
    min-width: 10rem;
}

.stat-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: var(--p-lingo-font-size-small);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-400);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.stat-icon {
    font-size: 1rem;
    color: var(--p-primary-500);
}

.stat-count {
    font-size: 2.5rem;
    font-weight: 600;
    color: var(--p-text-color);
    line-height: 1;
    padding-top: 0.25rem;
}

.type-breakdown {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.type-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0.75rem;
    border-radius: 1rem;
    background: var(--p-surface-100);
    border: 0.0625rem solid var(--p-surface-border);
    font-size: var(--p-lingo-font-size-smallnormal);
}

.type-label {
    color: var(--p-text-color);
}

.type-count {
    font-weight: 600;
    color: var(--p-primary-500);
}

.dashboard-section {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.section-title {
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
    margin: 0;
    border-bottom: 0.0625rem solid var(--p-surface-border);
    padding-bottom: 0.5rem;
}

.missing-filters {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.hint-text {
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-inputtext-placeholder-color);
    margin: 0;
}

.resource-link {
    color: var(--p-primary-500);
    text-decoration: none;
}

.resource-link:hover {
    text-decoration: underline;
}

.no-data {
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-light);
    color: var(--p-inputtext-placeholder-color);
}

.results-count {
    font-size: var(--p-lingo-font-size-xsmall);
    color: var(--p-neutral-400);
    margin: 0.25rem 0 0 0;
}

:deep(.p-datatable-tbody > tr > td) {
    font-size: var(--p-lingo-font-size-smallnormal);
    padding: 0.4rem 0.75rem;
}

:deep(.p-datatable-column-title) {
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-400);
}

:deep(.p-card-title) {
    font-size: var(--p-lingo-font-size-small);
}

:deep(.p-card-body) {
    padding: 1rem;
}
</style>
