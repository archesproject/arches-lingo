<script setup lang="ts">
import { computed, ref } from "vue";

import { useGettext } from "vue3-gettext";

import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Select from "primevue/select";
import Tag from "primevue/tag";

import {
    OUTCOME_ADD,
    buildOutcomeLabels,
    describeOutcome,
} from "@/arches_lingo/components/generic/MatchLinkImportDialog/utils.ts";
import { SECONDARY, SUCCESS } from "@/arches_lingo/constants.ts";

import type {
    MatchLinkImportOutcome,
    MatchLinkImportPreview,
} from "@/arches_lingo/types.ts";

const ROWS_PER_PAGE = 10;

const { preview } = defineProps<{
    preview: MatchLinkImportPreview;
}>();

const { $gettext, $ngettext } = useGettext();
const outcomeLabels = buildOutcomeLabels($gettext);

const selectedOutcome = ref<MatchLinkImportOutcome | null>(null);

const outcomeTotals = computed(() =>
    (
        Object.entries(preview.counts_by_outcome) as [
            MatchLinkImportOutcome,
            number,
        ][]
    ).map(([outcome, count]) => ({
        outcome,
        count,
        label: describeOutcome(outcomeLabels, outcome),
    })),
);

const visibleRows = computed(() =>
    selectedOutcome.value
        ? preview.rows.filter((row) => row.outcome === selectedOutcome.value)
        : preview.rows,
);

const hasInternalConceptRows = computed(() =>
    preview.rows.some((row) => row.is_internal_concept),
);

function outcomeSeverity(outcome: MatchLinkImportOutcome): string {
    return outcome === OUTCOME_ADD ? SUCCESS : SECONDARY;
}
</script>

<template>
    <div class="match-link-import-preview">
        <div class="totals">
            <span class="total-rows">
                {{
                    $ngettext(
                        "%{count} row checked",
                        "%{count} rows checked",
                        preview.total_rows,
                        { count: String(preview.total_rows) },
                    )
                }}
            </span>
            <Tag
                v-for="total in outcomeTotals"
                :key="total.outcome"
                :severity="outcomeSeverity(total.outcome)"
                :value="
                    $gettext('%{label}: %{count}', {
                        label: total.label,
                        count: String(total.count),
                    })
                "
            />
        </div>

        <Select
            v-model="selectedOutcome"
            class="outcome-filter"
            option-label="label"
            option-value="outcome"
            show-clear
            :options="outcomeTotals"
            :placeholder="$gettext('All rows')"
            :aria-label="$gettext('Show rows with this outcome')"
        />

        <p
            v-if="hasInternalConceptRows"
            class="internal-concept-note"
        >
            {{
                $gettext(
                    "Some URIs belong to concepts in Lingo. Those links are added one way only; use Find Matching Concepts for a two-way link.",
                )
            }}
        </p>

        <DataTable
            paginator
            size="small"
            :value="visibleRows"
            :rows="ROWS_PER_PAGE"
            :table-props="{
                'aria-label': $gettext('Rows in the match links file'),
            }"
        >
            <Column
                field="row_number"
                :header="$gettext('Row')"
            />
            <Column :header="$gettext('Concept')">
                <template #body="{ data }">
                    <span>{{ data.concept_label || data.concept_id }}</span>
                </template>
            </Column>
            <Column :header="$gettext('Match URI')">
                <template #body="{ data }">
                    <span class="match-uri">{{ data.match_uri }}</span>
                    <span
                        v-if="data.is_internal_concept"
                        class="internal-concept"
                    >
                        <i
                            class="pi pi-info-circle"
                            aria-hidden="true"
                        />
                        {{ $gettext("Lingo concept: linked one way only") }}
                    </span>
                </template>
            </Column>
            <Column
                field="match_type"
                :header="$gettext('Type')"
            />
            <Column :header="$gettext('Outcome')">
                <template #body="{ data }">
                    <Tag
                        :severity="outcomeSeverity(data.outcome)"
                        :value="
                            describeOutcome(
                                outcomeLabels,
                                data.outcome as MatchLinkImportOutcome,
                            )
                        "
                    />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<style scoped>
.match-link-import-preview {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.match-link-import-preview .totals {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
}

.match-link-import-preview .totals .total-rows {
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-text-muted-color);
}

.match-link-import-preview .outcome-filter {
    align-self: flex-start;
    min-width: 16rem;
}

.match-link-import-preview .match-uri {
    word-break: break-all;
}

.match-link-import-preview .internal-concept-note {
    margin: 0;
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-text-muted-color);
}

.match-link-import-preview .internal-concept {
    display: flex;
    gap: 0.375rem;
    align-items: baseline;
    margin-block-start: 0.25rem;
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-text-muted-color);
}
</style>
