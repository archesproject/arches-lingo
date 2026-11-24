<script setup lang="ts">
import { computed } from "vue";

import { useGettext } from "vue3-gettext";

import Message from "primevue/message";
import Tag from "primevue/tag";

import {
    buildOutcomeLabels,
    summarizeOutcomeCounts,
} from "@/arches_lingo/components/generic/MatchLinkImportDialog/utils.ts";
import { SUCCESS, WARN } from "@/arches_lingo/constants.ts";

import type { MatchLinkImportOutcomeCounts } from "@/arches_lingo/components/generic/MatchLinkImportDialog/types.ts";

const { outcomeCounts, errorMessage } = defineProps<{
    outcomeCounts: MatchLinkImportOutcomeCounts;
    errorMessage: string;
}>();

const { $gettext } = useGettext();
const outcomeLabels = buildOutcomeLabels($gettext);

const outcomeTotals = computed(() =>
    summarizeOutcomeCounts($gettext, outcomeLabels, outcomeCounts),
);
</script>

<template>
    <Message
        :severity="errorMessage ? WARN : SUCCESS"
        :closable="false"
    >
        <div class="match-link-import-result">
            <span>{{ $gettext("Import finished.") }}</span>
            <span v-if="errorMessage">{{ errorMessage }}</span>
            <Tag
                v-for="outcomeTotal in outcomeTotals"
                :key="outcomeTotal.outcome"
                :severity="outcomeTotal.severity"
                :value="outcomeTotal.text"
            />
        </div>
    </Message>
</template>

<style scoped>
.match-link-import-result {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
}
</style>
