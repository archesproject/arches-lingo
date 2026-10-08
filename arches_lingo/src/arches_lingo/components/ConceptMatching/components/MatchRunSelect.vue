<script setup lang="ts">
import { computed } from "vue";

import { storeToRefs } from "pinia";
import { useGettext } from "vue3-gettext";

import Select from "primevue/select";

import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

import type { ConceptMatchRun } from "@/arches_lingo/types.ts";

const { runs, activeRunId } = defineProps<{
    runs: ConceptMatchRun[];
    activeRunId: number | null;
}>();

const emit = defineEmits<{
    (event: "run-selected", payload: { runId: number | null }): void;
}>();

const { $gettext, $ngettext } = useGettext();
const { selectedLanguage } = storeToRefs(useLanguageStore());

const activeRunDescription = computed(function () {
    const activeRun = runs.find((run) => run.id === activeRunId);
    if (!activeRun) return "";
    const counts = {
        name: activeRun.name,
        pending: String(activeRun.pending_count),
        total: String(activeRun.candidate_count),
    };
    return activeRun.name
        ? $gettext("%{name} — %{pending} of %{total} left to review", counts)
        : $gettext("%{pending} of %{total} left to review", counts);
});

function describeRunOption(run: ConceptMatchRun): string {
    const details = {
        name: run.name,
        count: String(run.candidate_count),
        started: new Date(run.created).toLocaleString(
            selectedLanguage.value.code,
        ),
        creator: run.created_by ?? $gettext("Command line"),
    };
    return run.name
        ? $ngettext(
              "%{name} — %{count} pair — %{started} — %{creator}",
              "%{name} — %{count} pairs — %{started} — %{creator}",
              run.candidate_count,
              details,
          )
        : $ngettext(
              "%{count} pair — %{started} — %{creator}",
              "%{count} pairs — %{started} — %{creator}",
              run.candidate_count,
              details,
          );
}

function onRunChosen(runId: number | null): void {
    emit("run-selected", { runId });
}
</script>

<template>
    <Select
        class="run-select"
        option-value="id"
        :model-value="activeRunId"
        :options="runs"
        :option-label="describeRunOption"
        :placeholder="$gettext('No runs yet')"
        :disabled="!runs.length"
        :aria-label="$gettext('Match run')"
        @update:model-value="onRunChosen"
    >
        <template #value="{ placeholder }">
            <span>{{ activeRunDescription || placeholder }}</span>
        </template>
    </Select>
</template>

<style scoped>
.run-select {
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
}
</style>
