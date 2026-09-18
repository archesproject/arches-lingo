<script setup lang="ts">
import { computed, ref } from "vue";

import { useGettext } from "vue3-gettext";
import { storeToRefs } from "pinia";

import Button from "primevue/button";
import Dialog from "primevue/dialog";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import Step from "primevue/step";
import StepList from "primevue/steplist";
import StepPanel from "primevue/steppanel";
import StepPanels from "primevue/steppanels";
import Stepper from "primevue/stepper";

import MergeComparison from "@/arches_lingo/components/concept/ConceptMerge/components/MergeComparison.vue";
import MergeConceptPicker from "@/arches_lingo/components/concept/ConceptMerge/components/MergeConceptPicker.vue";
import MergeConfirmation from "@/arches_lingo/components/concept/ConceptMerge/components/MergeConfirmation.vue";

import { fetchLingoResource, mergeConcepts } from "@/arches_lingo/api.ts";
import { buildMergePayload } from "@/arches_lingo/components/concept/ConceptMerge/utils.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import {
    ERROR,
    SECONDARY,
    STRATEGY_REPARENT_TO_SURVIVOR,
} from "@/arches_lingo/constants.ts";
import {
    MERGE_STEP_COMPARE,
    MERGE_STEP_CONFIRM,
    MERGE_STEP_SELECT,
} from "@/arches_lingo/components/concept/ConceptMerge/constants.ts";

import type {
    MergeRetirementStrategy,
    ResourceInstanceResult,
    SearchResultItem,
} from "@/arches_lingo/types.ts";
import type { MergeSelectionState } from "@/arches_lingo/components/concept/ConceptMerge/types.ts";

const { survivorConcept, survivorLabel, schemeId, graphSlug } = defineProps<{
    survivorConcept: ResourceInstanceResult;
    survivorLabel: string | undefined;
    schemeId: string;
    graphSlug: string;
}>();

const emit = defineEmits<{
    cancel: [];
    merged: [];
}>();

const { $gettext } = useGettext();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

// A fixed frame: the dialog keeps one size on every step and for every set of
// search results, and the step body scrolls inside it. It is sized for the compare
// step, which is the widest and longest of the three.
const DIALOG_SIZE = {
    width: "84rem",
    maxWidth: "94vw",
    height: "88vh",
};

const dialogPassThrough = {
    content: {
        style: {
            display: "flex",
            flexDirection: "column",
            flex: "1",
            minHeight: "0",
            overflow: "hidden",
        },
    },
};

const currentStep = ref(MERGE_STEP_SELECT);
const selectedConcept = ref<SearchResultItem>();
const absorbedConcept = ref<ResourceInstanceResult>();
const isLoadingAbsorbedConcept = ref(false);
const fetchError = ref<string | null>(null);
const createExactMatchTiles = ref(true);
const retireAbsorbedConcept = ref(true);
const retirementStrategy = ref<MergeRetirementStrategy>(
    STRATEGY_REPARENT_TO_SURVIVOR,
);
const selectionState = ref<MergeSelectionState>();
const isMerging = ref(false);
const mergeError = ref<string | null>(null);

const canCompare = computed(function () {
    return Boolean(absorbedConcept.value) && !isLoadingAbsorbedConcept.value;
});

const absorbedLabel = computed(function () {
    if (!selectedConcept.value) {
        return undefined;
    }
    return getItemLabel(
        selectedConcept.value,
        selectedLanguage.value.code,
        systemLanguage.value.code,
    ).value;
});

const canConfirm = computed(function () {
    return Boolean(
        selectionState.value &&
            !selectionState.value.hasUnresolvedPrefLabelConflicts,
    );
});

async function onConceptSelected(concept: SearchResultItem) {
    selectedConcept.value = concept;
    absorbedConcept.value = undefined;
    // The comparison step is unmounted while the picker is showing, so it cannot
    // clear its own state. Left behind, it would keep the confirm step reachable
    // with the previous concept's tiles still selected.
    selectionState.value = undefined;
    isLoadingAbsorbedConcept.value = true;
    fetchError.value = null;
    try {
        absorbedConcept.value = await fetchLingoResource(graphSlug, concept.id);
    } catch (error) {
        fetchError.value =
            error instanceof Error ? error.message : String(error);
    } finally {
        isLoadingAbsorbedConcept.value = false;
    }
}

function onSelectionStateChange(updatedState: MergeSelectionState) {
    selectionState.value = updatedState;
}

async function onMergeConfirmed() {
    if (!selectionState.value || !absorbedConcept.value) {
        return;
    }

    isMerging.value = true;
    mergeError.value = null;
    try {
        await mergeConcepts(
            survivorConcept.resourceinstanceid,
            buildMergePayload(
                absorbedConcept.value.resourceinstanceid,
                selectionState.value.sectionComparisons,
                selectionState.value.prefLabelConflicts,
                selectionState.value.prefLabelWinnerByLanguage,
                {
                    createExactMatchTiles: createExactMatchTiles.value,
                    retireAbsorbedConcept: retireAbsorbedConcept.value,
                    retirementStrategy: retirementStrategy.value,
                },
            ),
        );
        emit("merged");
    } catch (error) {
        mergeError.value =
            error instanceof Error ? error.message : String(error);
    } finally {
        isMerging.value = false;
    }
}
</script>

<template>
    <Dialog
        :visible="true"
        :modal="true"
        :header="$gettext('Merge Concepts')"
        class="concept-merge-dialog"
        :closable="!isMerging"
        :style="DIALOG_SIZE"
        :pt="dialogPassThrough"
        @update:visible="!isMerging && emit('cancel')"
    >
        <Stepper
            v-model:value="currentStep"
            class="merge-stepper"
        >
            <StepList>
                <Step :value="MERGE_STEP_SELECT">
                    {{ $gettext("Choose concept") }}
                </Step>
                <Step
                    :value="MERGE_STEP_COMPARE"
                    :disabled="!canCompare"
                >
                    {{ $gettext("Choose values") }}
                </Step>
                <Step
                    :value="MERGE_STEP_CONFIRM"
                    :disabled="!canConfirm"
                >
                    {{ $gettext("Confirm") }}
                </Step>
            </StepList>

            <StepPanels>
                <StepPanel
                    v-slot="{ activateCallback }"
                    :value="MERGE_STEP_SELECT"
                >
                    <div class="merge-step">
                        <div class="merge-step-body merge-step-body--fill">
                            <p class="merge-step-intro">
                                {{
                                    $gettext(
                                        'Choose the concept to merge into "%{name}". Its values are copied across, and it can be retired afterwards.',
                                        { name: survivorLabel ?? "" },
                                    )
                                }}
                            </p>

                            <MergeConceptPicker
                                :scheme-id="schemeId"
                                :survivor-concept-id="
                                    survivorConcept.resourceinstanceid
                                "
                                :selected-concept-id="selectedConcept?.id"
                                @select="onConceptSelected"
                            />

                            <Message
                                v-if="fetchError"
                                :severity="ERROR"
                                :closable="false"
                            >
                                {{ fetchError }}
                            </Message>
                        </div>
                        <div class="merge-step-actions">
                            <Button
                                :label="$gettext('Cancel')"
                                :severity="SECONDARY"
                                :outlined="true"
                                @click="emit('cancel')"
                            />
                            <Button
                                :label="$gettext('Next')"
                                :disabled="!canCompare"
                                :loading="isLoadingAbsorbedConcept"
                                @click="activateCallback(MERGE_STEP_COMPARE)"
                            />
                        </div>
                    </div>
                </StepPanel>

                <StepPanel
                    v-slot="{ activateCallback }"
                    :value="MERGE_STEP_COMPARE"
                >
                    <div class="merge-step">
                        <div class="merge-step-body">
                            <ProgressSpinner
                                v-if="isLoadingAbsorbedConcept"
                                class="merge-spinner"
                            />
                            <MergeComparison
                                v-else-if="absorbedConcept"
                                :survivor-concept-id="
                                    survivorConcept.resourceinstanceid
                                "
                                :survivor-aliased-data="
                                    survivorConcept.aliased_data
                                "
                                :absorbed-aliased-data="
                                    absorbedConcept.aliased_data
                                "
                                @update:selection-state="onSelectionStateChange"
                            />
                        </div>
                        <div class="merge-step-actions">
                            <Button
                                :label="$gettext('Back')"
                                :severity="SECONDARY"
                                :outlined="true"
                                @click="activateCallback(MERGE_STEP_SELECT)"
                            />
                            <Button
                                :label="$gettext('Next')"
                                :disabled="!canConfirm"
                                @click="activateCallback(MERGE_STEP_CONFIRM)"
                            />
                        </div>
                    </div>
                </StepPanel>

                <StepPanel
                    v-slot="{ activateCallback }"
                    :value="MERGE_STEP_CONFIRM"
                >
                    <div class="merge-step">
                        <div class="merge-step-body">
                            <MergeConfirmation
                                v-if="absorbedConcept"
                                :absorbed-concept-id="
                                    absorbedConcept.resourceinstanceid
                                "
                                :survivor-label="survivorLabel"
                                :absorbed-label="absorbedLabel"
                                :section-summaries="
                                    selectionState?.sectionSummaries ?? []
                                "
                                :create-exact-match-tiles="
                                    createExactMatchTiles
                                "
                                :retire-absorbed-concept="retireAbsorbedConcept"
                                :retirement-strategy="retirementStrategy"
                                @update:create-exact-match-tiles="
                                    createExactMatchTiles = $event
                                "
                                @update:retire-absorbed-concept="
                                    retireAbsorbedConcept = $event
                                "
                                @update:retirement-strategy="
                                    retirementStrategy = $event
                                "
                            />

                            <Message
                                v-if="mergeError"
                                :severity="ERROR"
                                :closable="false"
                            >
                                {{ mergeError }}
                            </Message>
                        </div>
                        <div class="merge-step-actions">
                            <Button
                                :label="$gettext('Back')"
                                :severity="SECONDARY"
                                :outlined="true"
                                :disabled="isMerging"
                                @click="activateCallback(MERGE_STEP_COMPARE)"
                            />
                            <Button
                                :label="$gettext('Merge')"
                                :disabled="!canConfirm || isMerging"
                                :loading="isMerging"
                                @click="onMergeConfirmed"
                            />
                        </div>
                    </div>
                </StepPanel>
            </StepPanels>
        </Stepper>
    </Dialog>
</template>

<style scoped>
.merge-stepper {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    gap: 1rem;
}

/* The default markers sit on a full-width rule with very long separators, which
   reads as decoration rather than progress at this dialog width. Tightening the
   markers and closing the list with a divider keeps the three steps legible. */
.merge-stepper :deep(.p-steplist) {
    flex: none;
    padding: 0 0 1rem 0;
    border-bottom: 0.0625rem solid var(--p-content-border-color);
}

.merge-stepper :deep(.p-step-header) {
    gap: 0.5rem;
    padding: 0;
}

.merge-stepper :deep(.p-step-number) {
    width: 1.75rem;
    min-width: 1.75rem;
    height: 1.75rem;
    font-size: var(--p-lingo-font-size-smallnormal);
}

.merge-stepper :deep(.p-step-title) {
    font-size: var(--p-lingo-font-size-normal);
    white-space: nowrap;
}

.merge-stepper :deep(.p-step-active) .p-step-title {
    font-weight: var(--p-lingo-font-weight-bold);
}

.merge-stepper :deep(.p-stepper-separator) {
    margin: 0 1rem;
}

.merge-stepper :deep(.p-steppanels) {
    display: flex;
    flex: 1;
    min-height: 0;
    padding: 0;
}

.merge-stepper :deep(.p-steppanel) {
    flex: 1;
    min-height: 0;
}

.merge-step {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
}

.merge-step-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding-inline-end: 0.5rem;
}

/* The picker manages its own scrolling, so this step does not add a second one. */
.merge-step-body--fill {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding-inline-end: 0;
}

.merge-step-intro {
    margin: 0 0 0.75rem 0;
    font-size: var(--p-lingo-font-size-normal);
}

.merge-step-actions {
    display: flex;
    flex: none;
    justify-content: flex-end;
    gap: 0.5rem;
    padding-top: 1rem;
    border-top: 0.0625rem solid var(--p-content-border-color);
}

.merge-spinner {
    width: 2.5rem;
    height: 2.5rem;
}
</style>
