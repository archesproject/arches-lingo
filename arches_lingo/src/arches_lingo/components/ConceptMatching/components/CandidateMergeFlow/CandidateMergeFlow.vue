<script setup lang="ts">
import { computed, ref } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import ConceptMergeDialog from "@/arches_lingo/components/concept/ConceptMerge/ConceptMergeDialog.vue";
import MergeDirectionDialog from "@/arches_lingo/components/ConceptMatching/components/CandidateMergeFlow/components/MergeDirectionDialog.vue";

import { fetchLingoResource } from "@/arches_lingo/api.ts";
import { useErrorToast } from "@/arches_lingo/components/ConceptMatching/composables/useErrorToast.ts";
import { useLocalizedLabel } from "@/arches_lingo/components/ConceptMatching/composables/useLocalizedLabel.ts";
import {
    buildPreselectedConcept,
    resolveMergeSides,
} from "@/arches_lingo/components/ConceptMatching/utils.ts";
import { DEFAULT_TOAST_LIFE, SUCCESS } from "@/arches_lingo/constants.ts";

import type {
    MatchedConceptSummary,
    ResourceInstanceResult,
} from "@/arches_lingo/types.ts";
import type { MergeDirection } from "@/arches_lingo/components/ConceptMatching/types.ts";

const CONCEPT_GRAPH_SLUG = "concept";
const MERGED_EVENT = "merged" as const;
const CANCEL_EVENT = "cancel" as const;

const { conceptA, conceptB } = defineProps<{
    conceptA: MatchedConceptSummary;
    conceptB: MatchedConceptSummary;
}>();

const emit = defineEmits<{
    (event: typeof MERGED_EVENT): void;
    (event: typeof CANCEL_EVENT): void;
}>();

const { $gettext } = useGettext();
const toast = useToast();
const { reportError } = useErrorToast();
const { labelOf } = useLocalizedLabel();

// A pair has no direction, but a merge does, so which concept survives is
// chosen first; only then is the survivor fetched in the shape the merge
// dialog expects.
const survivorResource = ref<ResourceInstanceResult | null>(null);
const absorbedConceptId = ref<string | null>(null);
const isPreparingMerge = ref(false);

const mergeSides = computed(() =>
    absorbedConceptId.value
        ? resolveMergeSides(conceptA, conceptB, absorbedConceptId.value)
        : null,
);

// Computed rather than built in the template: the merge dialog restarts its
// comparison whenever this object changes.
const preselectedAbsorbedConcept = computed(() =>
    mergeSides.value
        ? buildPreselectedConcept(mergeSides.value.absorbed)
        : undefined,
);

async function onDirectionChosen({
    survivorId,
    absorbedId,
}: MergeDirection): Promise<void> {
    isPreparingMerge.value = true;
    try {
        survivorResource.value = await fetchLingoResource(
            CONCEPT_GRAPH_SLUG,
            survivorId,
        );
        absorbedConceptId.value = absorbedId;
    } catch (error) {
        reportError(error, $gettext("Could not open the merge."));
        emit(CANCEL_EVENT);
    } finally {
        isPreparingMerge.value = false;
    }
}

function onMerged(): void {
    toast.add({
        severity: SUCCESS,
        life: DEFAULT_TOAST_LIFE,
        summary: $gettext("Concepts merged"),
    });
    emit(MERGED_EVENT);
}
</script>

<template>
    <MergeDirectionDialog
        v-if="!survivorResource || !mergeSides"
        :concept-a="conceptA"
        :concept-b="conceptB"
        :is-loading="isPreparingMerge"
        @direction-chosen="onDirectionChosen"
        @cancel="emit(CANCEL_EVENT)"
    />

    <ConceptMergeDialog
        v-else
        :graph-slug="CONCEPT_GRAPH_SLUG"
        :survivor-concept="survivorResource"
        :survivor-label="labelOf(mergeSides.survivor)"
        :scheme-id="mergeSides.survivor.scheme_id ?? ''"
        :preselected-concept="preselectedAbsorbedConcept"
        @merged="onMerged"
        @cancel="emit(CANCEL_EVENT)"
    />
</template>
