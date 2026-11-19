<script setup lang="ts">
import { nextTick, provide, ref, useId, watch } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import FacetGroup from "@/arches_lingo/components/advanced-search/FacetGroup.vue";

import type {
    AdvancedSearchOptions,
    ConceptSetItem,
    SearchCondition,
    SearchGroup,
} from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();

const props = defineProps<{
    queryGroup: SearchGroup;
    options: AdvancedSearchOptions;
    conceptSets: ConceptSetItem[];
    isSearching: boolean;
}>();

const emit = defineEmits<{
    (e: "update:queryGroup", group: SearchGroup): void;
    (e: "search"): void;
    (e: "clear"): void;
}>();

provide("executeSearch", () => emit("search"));

const queryPanelRef = ref<HTMLElement | null>(null);
const querySummaryId = useId();
const querySummary = ref("");

// Read from the rendered controls so labels that load later are included.
function describeCondition(conditionElement: HTMLElement) {
    const controls = conditionElement.querySelectorAll<HTMLElement>(
        ".p-togglebutton, .p-select-label, input.p-inputtext",
    );
    return Array.from(controls)
        .map((control) => {
            if (control instanceof HTMLInputElement) {
                return control.value.trim() ? `"${control.value.trim()}"` : "";
            }
            if (control.classList.contains("p-togglebutton")) {
                return control.getAttribute("aria-pressed") === "true"
                    ? control.textContent?.trim()
                    : "";
            }
            return control.classList.contains("p-placeholder")
                ? ""
                : control.textContent?.trim();
        })
        .filter(Boolean)
        .join(" ");
}

function describeGroup(group: SearchGroup): string {
    const operatorText =
        group.operator === "and" ? $gettext("and") : $gettext("or");
    return group.conditions
        .map((child: SearchCondition | SearchGroup) => {
            if ("operator" in child) {
                const groupDescription = describeGroup(child);
                return groupDescription ? `(${groupDescription})` : "";
            }
            const conditionElement =
                queryPanelRef.value?.querySelector<HTMLElement>(
                    `[data-condition-id="${child.id}"]`,
                );
            return conditionElement ? describeCondition(conditionElement) : "";
        })
        .filter(Boolean)
        .join(` ${operatorText} `);
}

function updateQuerySummary() {
    const queryDescription = describeGroup(props.queryGroup);
    querySummary.value = queryDescription
        ? $gettext(
              "Search for concepts where %{query}",
              { query: queryDescription },
              true,
          )
        : "";
}

watch(
    () => props.queryGroup,
    async () => {
        await nextTick();
        updateQuerySummary();
    },
    { deep: true, immediate: true },
);
</script>

<template>
    <div
        ref="queryPanelRef"
        class="query-panel"
    >
        <FacetGroup
            :group="props.queryGroup"
            :options="props.options"
            :concept-sets="props.conceptSets"
            :depth="0"
            @update:group="emit('update:queryGroup', $event)"
        />

        <div class="search-actions">
            <Button
                :label="$gettext('Search')"
                icon="pi pi-search"
                :loading="props.isSearching"
                :aria-describedby="querySummary ? querySummaryId : undefined"
                @focus="updateQuerySummary"
                @click="emit('search')"
            />
            <span
                :id="querySummaryId"
                class="p-hidden-accessible"
                >{{ querySummary }}</span
            >
            <Button
                :label="$gettext('Clear')"
                icon="pi pi-eraser"
                severity="secondary"
                outlined
                @click="emit('clear')"
            />
        </div>
    </div>
</template>

<style scoped>
.query-panel {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    flex-shrink: 0;
}

.search-actions {
    display: flex;
    gap: 0.375rem;
    padding-top: 0.75rem;
    border-top: 0.0625rem solid var(--p-lingo-divider-color);
}

.search-actions :deep(.p-button) {
    font-size: var(--p-lingo-font-size-small);
    font-weight: var(--p-lingo-font-weight-normal);
    border-radius: 0.125rem;
}
</style>
