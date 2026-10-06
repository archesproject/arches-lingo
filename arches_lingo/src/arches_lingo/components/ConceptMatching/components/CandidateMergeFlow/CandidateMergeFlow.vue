<script setup lang="ts">
import { ref } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import ConceptMergeDialog from "@/arches_lingo/components/concept/ConceptMerge/ConceptMergeDialog.vue";
import MergeDirectionDialog from "@/arches_lingo/components/ConceptMatching/components/CandidateMergeFlow/components/MergeDirectionDialog.vue";

import { fetchLingoResource } from "@/arches_lingo/api.ts";
import { useErrorToast } from "@/arches_lingo/components/ConceptMatching/composables/useErrorToast.ts";
import { useLocalizedLabel } from "@/arches_lingo/components/ConceptMatching/composables/useLocalizedLabel.ts";
import { DEFAULT_TOAST_LIFE, SUCCESS } from "@/arches_lingo/constants.ts";

import type {
    MatchedConceptSummary,
    ResourceInstanceResult,
} from "@/arches_lingo/types.ts";
import type { MergeDirection } from "@/arches_lingo/components/ConceptMatching/types.ts";

const CONCEPT_GRAPH_SLUG = "concept";

const { conceptA, conceptB } = defineProps<{
    conceptA: MatchedConceptSummary;
    conceptB: MatchedConceptSummary;
}>();

const emit = defineEmits<{
    (event: "merged"): void;
    (event: "cancel"): void;
}>();

const { $gettext } = useGettext();
const toast = useToast();
const { reportError } = useErrorToast();
const { labelOf } = useLocalizedLabel();

const survivorResource = ref<ResourceInstanceResult | null>(null);
const mergeDirection = ref<MergeDirection | null>(null);
const isPreparingMerge = ref(false);

async function onDirectionChosen(
    chosenDirection: MergeDirection,
): Promise<void> {
    isPreparingMerge.value = true;
    try {
        survivorResource.value = await fetchLingoResource(
            CONCEPT_GRAPH_SLUG,
            chosenDirection.survivor.id,
        );
        mergeDirection.value = chosenDirection;
    } catch (error) {
        reportError(error, $gettext("Could not open the merge."));
        emit("cancel");
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
    emit("merged");
}
</script>

<template>
    <MergeDirectionDialog
        v-if="!survivorResource || !mergeDirection"
        :concept-a="conceptA"
        :concept-b="conceptB"
        :is-loading="isPreparingMerge"
        @direction-chosen="onDirectionChosen"
        @cancel="emit('cancel')"
    />

    <ConceptMergeDialog
        v-else
        :graph-slug="CONCEPT_GRAPH_SLUG"
        :survivor-concept="survivorResource"
        :survivor-label="labelOf(mergeDirection.survivor)"
        :scheme-id="mergeDirection.survivor.scheme_id ?? ''"
        :preselected-concept-id="mergeDirection.absorbed.id"
        @merged="onMerged"
        @cancel="emit('cancel')"
    />
</template>
