<script setup lang="ts">
import { computed } from "vue";

import { useGettext } from "vue3-gettext";
import { storeToRefs } from "pinia";

import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

import {
    SIGNAL_EXACT_LABEL,
    SIGNAL_SHARED_IDENTIFIER,
    SIGNAL_TRIGRAM,
} from "@/arches_lingo/components/concept-matching/constants.ts";

import type { ConceptMatchRun, Scheme } from "@/arches_lingo/types.ts";

const { run, schemes } = defineProps<{
    run: ConceptMatchRun;
    schemes: Scheme[];
}>();

const { $gettext } = useGettext();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

function parameter<ValueType>(key: string): ValueType | undefined {
    return run.parameters[key] as ValueType | undefined;
}

// Runs recorded before a scope could name more than one scheme stored a single
// id under its own key, so those are still read rather than shown as unscoped.
const scopedSchemeIds = computed(function () {
    const schemeIds = parameter<string[]>("scheme_ids");
    if (schemeIds?.length) {
        return schemeIds;
    }
    const legacySchemeId = parameter<string | null>("source_scheme_id");
    return legacySchemeId ? [legacySchemeId] : [];
});

const scopeText = computed(function () {
    if (!scopedSchemeIds.value.length) {
        return $gettext("Every scheme");
    }
    const namesById = new Map(
        schemes.map((scheme) => [
            scheme.id,
            getItemLabel(
                scheme,
                selectedLanguage.value.code,
                systemLanguage.value.code,
            ).value,
        ]),
    );
    return scopedSchemeIds.value
        .map(
            (schemeId) =>
                namesById.get(schemeId) ?? $gettext("a scheme since removed"),
        )
        .join(", ");
});

const signalLabelsBySignal = computed<Record<string, string>>(() => ({
    [SIGNAL_EXACT_LABEL]: $gettext("Labels that match exactly"),
    [SIGNAL_SHARED_IDENTIFIER]: $gettext("Concepts sharing a URI"),
    [SIGNAL_TRIGRAM]: $gettext("Labels that are merely similar"),
}));

const signalsText = computed(function () {
    const signals = parameter<string[]>("signals") ?? [];
    return signals
        .map((signal) => signalLabelsBySignal.value[signal] ?? signal)
        .join(", ");
});

const usedTrigram = computed(function () {
    return (parameter<string[]>("signals") ?? []).includes(SIGNAL_TRIGRAM);
});

const similarityText = computed(function () {
    return Number(parameter<number>("similarity_threshold") ?? 0).toFixed(2);
});

const narrowingText = computed(function () {
    const narrowings = [];
    if (parameter<boolean>("cross_scheme_only")) {
        narrowings.push($gettext("only pairs spanning two schemes"));
    }
    if (parameter<boolean>("same_language_only")) {
        narrowings.push($gettext("only labels in the same language"));
    }
    return narrowings.length ? narrowings.join(", ") : $gettext("None");
});

const startedText = computed(() => new Date(run.created).toLocaleString());
</script>

<template>
    <dl class="run-summary">
        <div
            v-if="run.name"
            class="run-summary-entry run-summary-name"
        >
            <dt>{{ $gettext("Name") }}</dt>
            <dd>{{ run.name }}</dd>
        </div>

        <div class="run-summary-entry">
            <dt>{{ $gettext("Schemes") }}</dt>
            <dd>{{ scopeText }}</dd>
        </div>

        <div class="run-summary-entry">
            <dt>{{ $gettext("Compared") }}</dt>
            <dd>{{ signalsText }}</dd>
        </div>

        <div
            v-if="usedTrigram"
            class="run-summary-entry"
        >
            <dt>{{ $gettext("Similarity") }}</dt>
            <dd>{{ similarityText }}</dd>
        </div>

        <div class="run-summary-entry">
            <dt>{{ $gettext("Narrowed by") }}</dt>
            <dd>{{ narrowingText }}</dd>
        </div>

        <div class="run-summary-entry">
            <dt>{{ $gettext("Started") }}</dt>
            <dd>{{ startedText }}</dd>
        </div>
    </dl>
</template>

<style scoped>
.run-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem 1.5rem;
    margin: 0;
    padding: 0.625rem 0.75rem;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.125rem;
    background: var(--p-content-background);
    font-size: var(--p-lingo-font-size-xxsmall);
}

.run-summary-entry {
    display: flex;
    gap: 0.375rem;
    min-width: 0;
}

.run-summary-entry dt {
    color: var(--p-inputtext-placeholder-color);
    white-space: nowrap;
}

.run-summary-entry dd {
    margin: 0;
    color: var(--p-header-item-label);
}

.run-summary-name dd {
    font-weight: var(--p-lingo-font-weight-bold);
}
</style>
