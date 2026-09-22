<script setup lang="ts">
import { computed } from "vue";

import { useGettext } from "vue3-gettext";
import { storeToRefs } from "pinia";

import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Tag from "primevue/tag";

import { RouterLink } from "vue-router";

import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { SIGNAL_SHARED_IDENTIFIER } from "@/arches_lingo/components/concept-matching/constants.ts";
import { SECONDARY } from "@/arches_lingo/constants.ts";

import type {
    ConceptMatchCandidate,
    MatchedConceptSummary,
} from "@/arches_lingo/types.ts";

const { candidate, isSelected } = defineProps<{
    candidate: ConceptMatchCandidate;
    isSelected: boolean;
}>();

const emit = defineEmits<{
    (event: "update:selected", candidateId: number, isSelected: boolean): void;
    (event: "merge", candidateId: number): void;
}>();

const { $gettext } = useGettext();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

function conceptName(concept: MatchedConceptSummary | null) {
    if (!concept) return $gettext("Unknown concept");
    return getItemLabel(
        concept,
        selectedLanguage.value.code,
        systemLanguage.value.code,
    ).value;
}

const reason = computed(function () {
    return candidate.signal === SIGNAL_SHARED_IDENTIFIER
        ? $gettext("Same URI: %{evidence}", { evidence: candidate.evidence })
        : $gettext("Same label: %{evidence}", { evidence: candidate.evidence });
});
</script>

<template>
    <div
        class="candidate-row"
        :class="{ selected: isSelected }"
    >
        <Checkbox
            :model-value="isSelected"
            :binary="true"
            :input-id="`candidate-${candidate.id}`"
            :aria-label="$gettext('Select this pair')"
            @update:model-value="
                emit('update:selected', candidate.id, $event as boolean)
            "
        />

        <div class="candidate-body">
            <div class="candidate-concepts">
                <span
                    v-for="(concept, index) in [
                        candidate.concept_a,
                        candidate.concept_b,
                    ]"
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
                        :to="{
                            name: routeNames.concept,
                            params: { id: concept.id },
                        }"
                        target="_blank"
                        rel="noopener"
                        :title="
                            $gettext('Open %{name} in a new tab', {
                                name: conceptName(concept),
                            })
                        "
                        :aria-label="
                            $gettext('Open %{name} in a new tab', {
                                name: conceptName(concept),
                            })
                        "
                        class="candidate-concept-link"
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
            severity="secondary"
            :value="$gettext('Across schemes')"
        />

        <Button
            icon="pi pi-sign-in"
            :label="$gettext('Merge')"
            :severity="SECONDARY"
            :outlined="true"
            class="candidate-merge-button"
            @click="emit('merge', candidate.id)"
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

.candidate-body {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 0;
    flex: 1;
}

.candidate-concepts {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.candidate-concept {
    display: flex;
    align-items: baseline;
    gap: 0.375rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    overflow-wrap: anywhere;
}

/* The same treatment links get in the concept report, so a concept name reads
   as a concept name wherever it appears. */
.candidate-concept-link {
    color: var(--p-primary-500);
    text-decoration: none;
}

.candidate-concept-link:hover,
.candidate-concept-link:focus-visible {
    color: var(--p-primary-700);
    text-decoration: underline;
}

.candidate-scheme {
    font-size: var(--p-lingo-font-size-xxsmall);
    color: var(--p-neutral-400);
}

.candidate-link-icon {
    color: var(--p-neutral-400);
}

.candidate-merge-button {
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
    white-space: nowrap;
}

.candidate-reason {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-inputtext-placeholder-color);
    overflow-wrap: anywhere;
}
</style>
