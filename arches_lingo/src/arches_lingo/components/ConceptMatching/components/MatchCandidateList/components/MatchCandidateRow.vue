<script setup lang="ts">
import { computed } from "vue";

import { useGettext } from "vue3-gettext";
import { RouterLink } from "vue-router";

import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Tag from "primevue/tag";

import { routeNames } from "@/arches_lingo/routes.ts";
import { useLocalizedLabel } from "@/arches_lingo/components/ConceptMatching/composables/useLocalizedLabel.ts";
import {
    SIGNAL_SHARED_IDENTIFIER,
    SIGNAL_TRIGRAM,
} from "@/arches_lingo/components/ConceptMatching/constants.ts";
import { SECONDARY } from "@/arches_lingo/constants.ts";

import type {
    ConceptMatchCandidate,
    MatchedConceptSummary,
} from "@/arches_lingo/types.ts";
import type { CandidateSelectionChange } from "@/arches_lingo/components/ConceptMatching/types.ts";

const SELECTION_CHANGED_EVENT = "selection-changed" as const;
const MERGE_REQUESTED_EVENT = "merge-requested" as const;

const {
    candidate,
    isSelected,
    isReviewable = true,
} = defineProps<{
    candidate: ConceptMatchCandidate;
    isSelected: boolean;
    isReviewable?: boolean;
}>();

const emit = defineEmits<{
    (
        event: typeof SELECTION_CHANGED_EVENT,
        payload: CandidateSelectionChange,
    ): void;
    (
        event: typeof MERGE_REQUESTED_EVENT,
        payload: { candidateId: number },
    ): void;
}>();

const { $gettext } = useGettext();
const { labelOf } = useLocalizedLabel();

const bothConceptsExist = computed(
    () => candidate.concept_a !== null && candidate.concept_b !== null,
);

const pairedConcepts = computed(() => [
    candidate.concept_a,
    candidate.concept_b,
]);

const selectionLabel = computed(() =>
    $gettext("Select %{first} and %{second}", {
        first: conceptName(candidate.concept_a),
        second: conceptName(candidate.concept_b),
    }),
);

const reason = computed(function () {
    if (candidate.signal === SIGNAL_SHARED_IDENTIFIER) {
        return $gettext("Same URI: %{evidence}", {
            evidence: candidate.evidence,
        });
    }
    if (candidate.signal === SIGNAL_TRIGRAM) {
        return $gettext("Similar labels (%{score}): %{evidence}", {
            score: candidate.score.toFixed(2),
            evidence: candidate.evidence,
        });
    }
    return $gettext("Same label: %{evidence}", {
        evidence: candidate.evidence,
    });
});

function conceptName(concept: MatchedConceptSummary | null): string {
    return concept ? labelOf(concept) : $gettext("Unknown concept");
}

function openInNewTabLabel(concept: MatchedConceptSummary): string {
    return $gettext("Open %{name} in a new tab", {
        name: conceptName(concept),
    });
}

function onSelectionChange(isChecked: boolean): void {
    emit(SELECTION_CHANGED_EVENT, {
        candidateId: candidate.id,
        isSelected: isChecked,
    });
}
</script>

<template>
    <div
        class="candidate-row"
        :class="{ selected: isSelected }"
    >
        <Checkbox
            v-if="isReviewable"
            :model-value="isSelected"
            :binary="true"
            :input-id="`candidate-${candidate.id}`"
            :aria-label="selectionLabel"
            @update:model-value="onSelectionChange"
        />

        <div class="candidate-body">
            <div class="candidate-concepts">
                <span
                    v-for="(concept, index) in pairedConcepts"
                    :key="concept?.id ?? index"
                    class="candidate-concept"
                >
                    <i
                        v-if="index === 1"
                        class="pi pi-arrows-h candidate-link-icon"
                        aria-hidden="true"
                    />
                    <RouterLink
                        v-if="concept"
                        class="candidate-concept-link"
                        target="_blank"
                        rel="noopener"
                        :to="{
                            name: routeNames.concept,
                            params: { id: concept.id },
                        }"
                        :title="openInNewTabLabel(concept)"
                        :aria-label="openInNewTabLabel(concept)"
                    >
                        {{ conceptName(concept) }}
                    </RouterLink>
                    <span v-else>{{ conceptName(concept) }}</span>

                    <span class="candidate-scheme">
                        {{ concept?.scheme_name }}
                    </span>
                </span>
            </div>

            <div class="candidate-reason">{{ reason }}</div>
        </div>

        <Tag
            v-if="candidate.is_cross_scheme"
            :severity="SECONDARY"
            :value="$gettext('Across schemes')"
        />

        <Button
            v-if="isReviewable && bothConceptsExist"
            class="candidate-merge-button"
            icon="pi pi-sign-in"
            :label="$gettext('Merge')"
            :severity="SECONDARY"
            :outlined="true"
            @click="emit(MERGE_REQUESTED_EVENT, { candidateId: candidate.id })"
        />
    </div>
</template>

<style scoped>
.candidate-row {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.625rem;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.125rem;
    background: var(--p-content-background);
}

.candidate-row.selected {
    border-color: var(--p-primary-color);
    background-color: var(--p-highlight-background);
}

.candidate-row .candidate-body {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 0;
    flex: 1;
}

.candidate-body .candidate-concepts {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.candidate-concepts .candidate-concept {
    display: flex;
    align-items: baseline;
    gap: 0.375rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    overflow-wrap: anywhere;
}

.candidate-concept .candidate-concept-link {
    color: var(--p-primary-color);
    text-decoration: none;
}

.candidate-concept .candidate-concept-link:hover,
.candidate-concept .candidate-concept-link:focus-visible {
    color: var(--p-primary-hover-color);
    text-decoration: underline;
}

.candidate-concept .candidate-scheme {
    font-size: var(--p-lingo-font-size-xxsmall);
    color: var(--p-text-muted-color);
}

.candidate-concept .candidate-link-icon {
    color: var(--p-text-muted-color);
}

.candidate-body .candidate-reason {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
    overflow-wrap: anywhere;
}

.candidate-row .candidate-merge-button {
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
    white-space: nowrap;
}
</style>
