<script setup lang="ts">
import { computed, inject, onMounted, ref, watch, type Ref } from "vue";
import { useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Column from "primevue/column";
import DataTable from "primevue/datatable";
import MultiSelect from "primevue/multiselect";
import Paginator from "primevue/paginator";
import Select from "primevue/select";
import Skeleton from "primevue/skeleton";
import Tag from "primevue/tag";

import { fetchLanguages } from "@/arches_component_lab/widgets/api.ts";
import {
    fetchDashboardStats,
    fetchLingoResources,
    fetchMissingTranslations,
} from "@/arches_lingo/api.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    selectedLanguageKey,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";
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

// --- Injected language preferences ---
const preferredLanguage = inject(selectedLanguageKey) as Ref<Language>;
const systemLanguage = inject(systemLanguageKey) as Language;

// --- Scheme filter ---
const schemes = ref<ResourceInstanceResult[]>([]);
const selectedSchemeIds = ref<string[]>([]);

// --- Dashboard stats ---
const isStatsLoading = ref(true);
const stats = ref<DashboardStats | null>(null);

// --- Activity period filter ---
interface ActivityPeriod {
    label: string;
    days: number;
}
const ACTIVITY_PERIODS: ActivityPeriod[] = [
    { label: $gettext("Last 24 hours"), days: 1 },
    { label: $gettext("Last 7 days"), days: 7 },
    { label: $gettext("Last 30 days"), days: 30 },
    { label: $gettext("Last 90 days"), days: 90 },
    { label: $gettext("All time"), days: 0 },
];
const selectedActivityPeriod = ref<ActivityPeriod>(ACTIVITY_PERIODS[1]);

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

function formatRelativeTime(timestamp: string | null): string {
    if (!timestamp) return "";
    const diffMs = Date.now() - new Date(timestamp).getTime();
    const diffMins = Math.floor(diffMs / 60_000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    if (diffMins < 1) return $gettext("Just now");
    if (diffMins < 60) return $gettext("%{n} min ago", { n: String(diffMins) });
    if (diffHours < 24)
        return $gettext("%{n} hr ago", { n: String(diffHours) });
    if (diffDays < 7) return $gettext("%{n}d ago", { n: String(diffDays) });
    return new Date(timestamp).toLocaleDateString();
}

function formatFullTimestamp(timestamp: string | null): string {
    if (!timestamp) return "";
    return new Date(timestamp).toLocaleString();
}

function getInitials(
    firstname: string,
    lastname: string,
    username: string,
): string {
    if (firstname || lastname) {
        return `${firstname?.[0] ?? ""}${lastname?.[0] ?? ""}`.toUpperCase();
    }
    return username?.[0]?.toUpperCase() ?? "?";
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

        <!-- Stat cards -->
        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-card-title">
                    <i class="pi pi-folder stat-icon" />
                    {{ $gettext("Schemes") }}
                </div>
                <Skeleton
                    v-if="isStatsLoading"
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
                    v-if="isStatsLoading"
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
                    v-if="isStatsLoading"
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
                    v-if="isStatsLoading"
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

        <!-- Breakdowns: two-column grid -->
        <div
            v-if="!isStatsLoading"
            class="breakdowns-grid"
        >
            <!-- Concepts by Type -->
            <section
                v-if="
                    stats?.concepts_by_type && stats.concepts_by_type.length > 0
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

            <!-- Labels by Type -->
            <section
                v-if="stats?.labels_by_type && stats.labels_by_type.length > 0"
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

            <!-- Labels by Language -->
            <section
                v-if="
                    stats?.labels_by_language &&
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

        <!-- Recent Activity -->
        <section class="dashboard-section">
            <div class="section-header">
                <h2>{{ $gettext("Recent Activity") }}</h2>
                <div class="filter-group">
                    <label
                        for="activity-period-filter"
                        class="filter-label"
                    >
                        {{ $gettext("Time frame") }}:
                    </label>
                    <Select
                        id="activity-period-filter"
                        v-model="selectedActivityPeriod"
                        :options="ACTIVITY_PERIODS"
                        option-label="label"
                        class="activity-period-select"
                    />
                </div>
            </div>
            <div v-if="isStatsLoading">
                <Skeleton
                    v-for="n in 5"
                    :key="n"
                    style="margin-bottom: 0.5rem"
                    height="2.25rem"
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
                    <div class="empty-state">
                        <i class="pi pi-inbox empty-icon" />
                        <span>{{ $gettext("No recent activity") }}</span>
                    </div>
                </template>
                <Column
                    :header="$gettext('When')"
                    style="width: 8rem"
                >
                    <template #body="slotProps">
                        <span
                            class="relative-time"
                            :title="
                                formatFullTimestamp(slotProps.data.timestamp)
                            "
                        >
                            {{ formatRelativeTime(slotProps.data.timestamp) }}
                        </span>
                    </template>
                </Column>
                <Column
                    field="edittype_label"
                    :header="$gettext('Action')"
                    style="width: 14rem"
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
                                getItemLabel(
                                    slotProps.data,
                                    preferredLanguage.code,
                                    systemLanguage.code,
                                ).value || slotProps.data.resource_id
                            }}
                        </a>
                    </template>
                </Column>
                <Column
                    :header="$gettext('Type')"
                    style="width: 6.5rem"
                >
                    <template #body="slotProps">
                        <Tag
                            :value="
                                slotProps.data.resource_type === 'scheme'
                                    ? $gettext('Scheme')
                                    : $gettext('Concept')
                            "
                            :severity="
                                slotProps.data.resource_type === 'scheme'
                                    ? 'success'
                                    : 'info'
                            "
                        />
                    </template>
                </Column>
                <Column
                    :header="$gettext('User')"
                    style="width: 11rem"
                >
                    <template #body="slotProps">
                        <div class="user-cell">
                            <span class="user-avatar">
                                {{
                                    getInitials(
                                        slotProps.data.user_firstname,
                                        slotProps.data.user_lastname,
                                        slotProps.data.user_username,
                                    )
                                }}
                            </span>
                            <span>
                                {{
                                    slotProps.data.user_firstname ||
                                    slotProps.data.user_lastname
                                        ? `${slotProps.data.user_firstname} ${slotProps.data.user_lastname}`.trim()
                                        : slotProps.data.user_username
                                }}
                            </span>
                        </div>
                    </template>
                </Column>
            </DataTable>
        </section>

        <!-- Missing Translations -->
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
                        v-model="selectedLanguage"
                        :options="languages"
                        option-label="name"
                        :placeholder="$gettext('Select a language')"
                        class="language-select"
                    />
                </div>
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
                        missingPage *
                        (missingTranslations?.results_per_page ?? 25)
                    "
                    @page="onPageChange"
                />
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
    gap: 1.25rem;
}

/* ── Header ── */
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

.filter-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.scheme-select,
.language-select {
    min-width: 14rem;
    border-radius: 0.125rem;
}

.activity-period-select {
    min-width: 9rem;
    border-radius: 0.125rem;
}

/* ── Stat cards ── */
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

/* ── Breakdowns grid ── */
.breakdowns-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
}

/* ── Sections ── */
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

/* ── Type breakdown chips ── */
.type-breakdown {
    display: flex;
    flex-wrap: wrap;
    gap: 0.375rem;
}

.type-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.25rem 0.625rem;
    border-radius: 0.125rem;
    background: var(--p-highlight-background);
    border: 0.0625rem solid var(--p-highlight-focus-background);
    font-size: var(--p-lingo-font-size-smallnormal);
}

.type-label {
    color: var(--p-content-color);
}

.type-count {
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-primary-500);
}

/* ── Activity table ── */
.relative-time {
    cursor: default;
    color: var(--p-inputtext-placeholder-color);
    font-size: var(--p-lingo-font-size-small);
}

.user-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.user-avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 50%;
    background: var(--p-primary-100);
    color: var(--p-primary-600);
    border: 0.0625rem solid var(--p-primary-300);
    font-size: 0.5625rem;
    font-weight: var(--p-lingo-font-weight-normal);
    flex-shrink: 0;
    text-transform: uppercase;
}

/* ── Empty states ── */
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

/* ── Misc ── */
.hint-text {
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-inputtext-placeholder-color);
    margin: 0;
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

:deep(.p-tag) {
    border-radius: 0.125rem;
    font-size: var(--p-lingo-font-size-xsmall);
}

/* ── Responsive ── */
@media (max-width: 960px) {
    .stats-row {
        grid-template-columns: repeat(2, 1fr);
    }

    .breakdowns-grid {
        grid-template-columns: 1fr;
    }

    .dashboard-header {
        flex-direction: column;
        align-items: flex-start;
    }

    .section-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.5rem;
    }
}
</style>
