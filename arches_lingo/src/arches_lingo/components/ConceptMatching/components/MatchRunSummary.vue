<script setup lang="ts">
import { computed } from "vue";

import { storeToRefs } from "pinia";
import { useGettext } from "vue3-gettext";

import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { useLocalizedLabel } from "@/arches_lingo/components/ConceptMatching/composables/useLocalizedLabel.ts";
import {
    SIGNAL_EXACT_LABEL,
    SIGNAL_SHARED_IDENTIFIER,
    SIGNAL_TRIGRAM,
} from "@/arches_lingo/components/ConceptMatching/constants.ts";

import type {
    ConceptMatchRun,
    ConceptMatchSignal,
    Scheme,
} from "@/arches_lingo/types.ts";

const { run, schemes } = defineProps<{
    run: ConceptMatchRun;
    schemes: Scheme[];
}>();

const { $gettext } = useGettext();
const { selectedLanguage } = storeToRefs(useLanguageStore());
const { labelOf } = useLocalizedLabel();

const scopeText = computed(function () {
    const schemeIds = run.parameters.scheme_ids;
    if (!schemeIds.length) {
        return $gettext("Every scheme");
    }
    const namesById = new Map(
        schemes.map((scheme) => [scheme.id, labelOf(scheme)]),
    );
    return formatList(
        schemeIds.map(
            (schemeId) =>
                namesById.get(schemeId) ?? $gettext("a scheme since removed"),
        ),
    );
});

const signalsText = computed(function () {
    const signalLabels: Record<ConceptMatchSignal, string> = {
        [SIGNAL_EXACT_LABEL]: $gettext("Labels that match exactly"),
        [SIGNAL_SHARED_IDENTIFIER]: $gettext("Concepts sharing a URI"),
        [SIGNAL_TRIGRAM]: $gettext("Labels that are merely similar"),
    };
    return formatList(
        run.parameters.signals.map((signal) => signalLabels[signal]),
    );
});

const usedTrigram = computed(() =>
    run.parameters.signals.includes(SIGNAL_TRIGRAM),
);

const similarityText = computed(() =>
    run.parameters.similarity_threshold.toFixed(2),
);

const narrowingText = computed(function () {
    const narrowings: string[] = [];
    if (run.parameters.cross_scheme_only) {
        narrowings.push($gettext("only pairs spanning two schemes"));
    }
    if (run.parameters.same_language_only) {
        narrowings.push($gettext("only labels in the same language"));
    }
    return narrowings.length ? formatList(narrowings) : $gettext("None");
});

const startedText = computed(() =>
    new Date(run.created).toLocaleString(selectedLanguage.value.code),
);

const startedByText = computed(
    () => run.created_by ?? $gettext("Command line"),
);

function formatList(items: string[]): string {
    return new Intl.ListFormat(selectedLanguage.value.code, {
        type: "conjunction",
    }).format(items);
}
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

        <div class="run-summary-entry">
            <dt>{{ $gettext("Started by") }}</dt>
            <dd>{{ startedByText }}</dd>
        </div>
    </dl>
</template>

<style scoped>
.run-summary {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
    gap: 0.75rem 1.5rem;
    margin: 0;
    padding: 0.75rem;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.125rem;
    background: var(--p-content-background);
}

.run-summary .run-summary-entry {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    min-width: 0;
}

.run-summary .run-summary-entry dt {
    font-size: var(--p-lingo-font-size-xxsmall);
    font-weight: var(--p-lingo-font-weight-bold);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--p-text-muted-color);
}

.run-summary .run-summary-entry dd {
    margin: 0;
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-header-item-label);
    overflow-wrap: anywhere;
}

.run-summary .run-summary-name dd {
    font-weight: var(--p-lingo-font-weight-bold);
}
</style>
