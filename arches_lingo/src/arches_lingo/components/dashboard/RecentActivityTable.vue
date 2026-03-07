<script setup lang="ts">
import { inject, type Ref } from "vue";
import { useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";

import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Select from "primevue/select";
import Skeleton from "primevue/skeleton";
import Tag from "primevue/tag";

import {
    selectedLanguageKey,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";

import type { Language } from "@/arches_component_lab/types.ts";
import type {
    DashboardActivityItem,
    DashboardStats,
} from "@/arches_lingo/types/dashboard.ts";

export interface ActivityPeriod {
    label: string;
    days: number;
}

const props = defineProps<{
    stats: DashboardStats | null;
    isLoading: boolean;
    activityPeriods: ActivityPeriod[];
    selectedActivityPeriod: ActivityPeriod;
}>();

const emit = defineEmits<{
    "update:selectedActivityPeriod": [value: ActivityPeriod];
}>();

const router = useRouter();
const { $gettext } = useGettext();

const preferredLanguage = inject(selectedLanguageKey) as Ref<Language>;
const systemLanguage = inject(systemLanguageKey) as Language;

function formatRelativeTime(timestamp: string | null): string {
    if (!timestamp) return "";
    const elapsedMilliseconds = Date.now() - new Date(timestamp).getTime();
    const elapsedMinutes = Math.floor(elapsedMilliseconds / 60_000);
    const elapsedHours = Math.floor(elapsedMinutes / 60);
    const elapsedDays = Math.floor(elapsedHours / 24);
    if (elapsedMinutes < 1) return $gettext("Just now");
    if (elapsedMinutes < 60)
        return $gettext("%{n} min ago", { n: String(elapsedMinutes) });
    if (elapsedHours < 24)
        return $gettext("%{n} hr ago", { n: String(elapsedHours) });
    if (elapsedDays < 7)
        return $gettext("%{n}d ago", { n: String(elapsedDays) });
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

function navigateToResource(item: DashboardActivityItem) {
    if (item.resource_type === "scheme") {
        navigateToScheme(item.resource_id);
    } else {
        navigateToConcept(item.resource_id);
    }
}

function getDisplayName(item: DashboardActivityItem): string {
    if (item.user_firstname || item.user_lastname) {
        return `${item.user_firstname} ${item.user_lastname}`.trim();
    }
    return item.user_username;
}
</script>

<template>
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
                    :model-value="props.selectedActivityPeriod"
                    :options="props.activityPeriods"
                    option-label="label"
                    class="activity-period-select"
                    @update:model-value="
                        emit('update:selectedActivityPeriod', $event)
                    "
                />
            </div>
        </div>
        <div v-if="isLoading">
            <Skeleton
                v-for="index in 5"
                :key="index"
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
                        :title="formatFullTimestamp(slotProps.data.timestamp)"
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
                        @click.prevent="navigateToResource(slotProps.data)"
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
                            {{ getDisplayName(slotProps.data) }}
                        </span>
                    </div>
                </template>
            </Column>
        </DataTable>
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

.activity-period-select {
    min-width: 9rem;
    border-radius: 0.125rem;
}

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

@media (max-width: 960px) {
    .section-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.5rem;
    }
}
</style>
