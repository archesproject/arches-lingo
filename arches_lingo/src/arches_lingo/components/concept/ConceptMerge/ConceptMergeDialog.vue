<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

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
import MergeConceptPair from "@/arches_lingo/components/concept/ConceptMerge/components/MergeConceptPair.vue";
import MergeConceptPicker from "@/arches_lingo/components/concept/ConceptMerge/components/MergeConceptPicker.vue";
import MergeConfirmation from "@/arches_lingo/components/concept/ConceptMerge/components/MergeConfirmation.vue";

import {
    fetchConceptAncestorPaths,
    fetchConceptMergePreview,
    fetchLingoResource,
    mergeConcepts,
} from "@/arches_lingo/api.ts";
import {
    buildSearchResultFromAncestorPath,
    buildMergePayload,
} from "@/arches_lingo/components/concept/ConceptMerge/utils.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import {
    DANGER,
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
    ConceptMergePreview,
    MergeRetirementStrategy,
    ResourceInstanceResult,
    SearchResultHierarchy,
    SearchResultItem,
} from "@/arches_lingo/types.ts";
import type { MergeSelectionState } from "@/arches_lingo/components/concept/ConceptMerge/types.ts";

// One fixed frame for every step, sized for the compare step, which is the
// widest and longest of the three. The step body scrolls inside it.
const DIALOG_SIZE = {
    width: "84rem",
    maxWidth: "94vw",
    height: "88vh",
};

// The chrome Lingo's other dialogs wear; see ExportThesauri.
const DIALOG_PASS_THROUGH = {
    root: {
        style: {
            fontFamily: "var(--p-lingo-font-family)",
            fontSize: "var(--p-lingo-font-size-small)",
            border: "0.125rem solid var(--p-dialog-color)",
            borderRadius: "0.25rem",
        },
    },
    header: {
        style: {
            background: "var(--p-navigation-header-color)",
            color: "var(--p-dialog-header-text-color)",
            borderRadius: "0",
            paddingBlock: "1.25rem",
            paddingInline: "1.5rem",
        },
    },
    title: {
        style: {
            fontSize: "var(--p-lingo-font-size-large)",
            fontWeight: "var(--p-lingo-font-weight-normal)",
            lineHeight: "1.2",
        },
    },
    content: {
        style: {
            display: "flex",
            flexDirection: "column",
            flex: "1",
            minHeight: "0",
            overflow: "hidden",
            padding: "1.25rem",
            paddingTop: "1rem",
        },
    },
};

const MERGE_STEP_ORDER = [
    MERGE_STEP_SELECT,
    MERGE_STEP_COMPARE,
    MERGE_STEP_CONFIRM,
];

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

const currentStep = ref(MERGE_STEP_SELECT);
const survivorSearchResult = ref<SearchResultItem>();
const selectedConcept = ref<SearchResultItem>();
const absorbedConcept = ref<ResourceInstanceResult>();
const mergePreview = ref<ConceptMergePreview>();
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

const previousStep = computed(function () {
    const stepIndex = MERGE_STEP_ORDER.indexOf(currentStep.value);
    return MERGE_STEP_ORDER[Math.max(stepIndex - 1, 0)];
});

const nextStep = computed(function () {
    const stepIndex = MERGE_STEP_ORDER.indexOf(currentStep.value);
    return MERGE_STEP_ORDER[
        Math.min(stepIndex + 1, MERGE_STEP_ORDER.length - 1)
    ];
});

const isCrossScheme = computed(function () {
    return mergePreview.value?.is_cross_scheme ?? false;
});

const canCompare = computed(function () {
    return (
        Boolean(absorbedConcept.value && mergePreview.value) &&
        !isLoadingAbsorbedConcept.value
    );
});

const canConfirm = computed(function () {
    return Boolean(
        selectionState.value &&
            !selectionState.value.hasUnresolvedPrefLabelConflicts,
    );
});

const isNextDisabled = computed(function () {
    if (currentStep.value === MERGE_STEP_SELECT) {
        return !canCompare.value;
    }
    return !canConfirm.value;
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

onMounted(loadSurvivorPath);

// Without its lineage the header falls back to the survivor's own label.
async function loadSurvivorPath() {
    try {
        const ancestorPaths: SearchResultHierarchy[] =
            await fetchConceptAncestorPaths(survivorConcept.resourceinstanceid);
        survivorSearchResult.value = buildSearchResultFromAncestorPath(
            ancestorPaths[0]?.searchResults ?? [],
        );
    } catch {
        survivorSearchResult.value = undefined;
    }
}

async function onConceptSelected(concept: SearchResultItem) {
    selectedConcept.value = concept;
    absorbedConcept.value = undefined;
    mergePreview.value = undefined;
    // The comparison step is unmounted while the picker is showing, so it cannot
    // clear its own state for the previous concept.
    selectionState.value = undefined;
    isLoadingAbsorbedConcept.value = true;
    fetchError.value = null;

    // Picking again before the first fetch returns leaves both in flight, and
    // only the response for the concept still selected may land.
    function isStillSelected() {
        return selectedConcept.value?.id === concept.id;
    }

    try {
        const [fetchedConcept, fetchedPreview] = await Promise.all([
            fetchLingoResource(graphSlug, concept.id),
            fetchConceptMergePreview(
                survivorConcept.resourceinstanceid,
                concept.id,
            ),
        ]);
        if (isStillSelected()) {
            absorbedConcept.value = fetchedConcept;
            mergePreview.value = fetchedPreview;
        }
    } catch (error) {
        if (isStillSelected()) {
            fetchError.value =
                error instanceof Error ? error.message : String(error);
        }
    } finally {
        if (isStillSelected()) {
            isLoadingAbsorbedConcept.value = false;
        }
    }
}

function onSelectionStateChange(updatedState: MergeSelectionState) {
    selectionState.value = updatedState;
}

function onVisibleChange() {
    if (!isMerging.value) {
        emit("cancel");
    }
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
                isCrossScheme.value,
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
        :pt="DIALOG_PASS_THROUGH"
        @update:visible="onVisibleChange"
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

            <MergeConceptPair
                class="merge-concept-pair-summary"
                :survivor-concept="survivorSearchResult"
                :survivor-label="survivorLabel"
                :absorbed-concept="selectedConcept"
                :is-cross-scheme="isCrossScheme"
            />

            <StepPanels>
                <StepPanel :value="MERGE_STEP_SELECT">
                    <div class="merge-step">
                        <div class="merge-step-body merge-step-body--fill">
                            <p class="merge-step-intro">
                                {{
                                    $gettext(
                                        'Choose the concept to merge into "%{name}". "%{name}" stays, the values you pick are copied onto it, and within the same scheme the other concept can be retired afterwards.',
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
                    </div>
                </StepPanel>

                <StepPanel :value="MERGE_STEP_COMPARE">
                    <div class="merge-step">
                        <div class="merge-step-body">
                            <ProgressSpinner
                                v-if="isLoadingAbsorbedConcept"
                                class="merge-spinner"
                            />
                            <MergeComparison
                                v-else-if="absorbedConcept && mergePreview"
                                :survivor-aliased-data="
                                    survivorConcept.aliased_data
                                "
                                :absorbed-aliased-data="
                                    absorbedConcept.aliased_data
                                "
                                :survivor-label="survivorLabel"
                                :absorbed-label="absorbedLabel"
                                :merge-preview="mergePreview"
                                @update:selection-state="onSelectionStateChange"
                            />
                        </div>
                    </div>
                </StepPanel>

                <StepPanel :value="MERGE_STEP_CONFIRM">
                    <div class="merge-step">
                        <div class="merge-step-body">
                            <MergeConfirmation
                                v-if="absorbedConcept"
                                v-model:create-exact-match-tiles="
                                    createExactMatchTiles
                                "
                                v-model:retire-absorbed-concept="
                                    retireAbsorbedConcept
                                "
                                v-model:retirement-strategy="retirementStrategy"
                                :absorbed-concept-id="
                                    absorbedConcept.resourceinstanceid
                                "
                                :survivor-concept-id="
                                    survivorConcept.resourceinstanceid
                                "
                                :survivor-label="survivorLabel"
                                :absorbed-label="absorbedLabel"
                                :section-summaries="
                                    selectionState?.sectionSummaries ?? []
                                "
                                :is-cross-scheme="isCrossScheme"
                            />

                            <Message
                                v-if="mergeError"
                                :severity="ERROR"
                                :closable="false"
                            >
                                {{ mergeError }}
                            </Message>
                        </div>
                    </div>
                </StepPanel>
            </StepPanels>
        </Stepper>

        <template #footer>
            <div class="footer">
                <Button
                    v-if="currentStep === MERGE_STEP_SELECT"
                    icon="pi pi-times"
                    :label="$gettext('Cancel')"
                    :severity="DANGER"
                    class="footer-button"
                    @click="emit('cancel')"
                />
                <Button
                    v-else
                    icon="pi pi-arrow-left"
                    :label="$gettext('Back')"
                    :severity="SECONDARY"
                    :outlined="true"
                    :disabled="isMerging"
                    class="footer-button"
                    @click="currentStep = previousStep"
                />

                <Button
                    v-if="currentStep === MERGE_STEP_CONFIRM"
                    icon="pi pi-check"
                    :label="$gettext('Merge')"
                    :disabled="!canConfirm || isMerging"
                    :loading="isMerging"
                    class="footer-button"
                    @click="onMergeConfirmed"
                />
                <Button
                    v-else
                    icon="pi pi-arrow-right"
                    icon-pos="right"
                    :label="$gettext('Next')"
                    :disabled="isNextDisabled"
                    :loading="isLoadingAbsorbedConcept"
                    class="footer-button"
                    @click="currentStep = nextStep"
                />
            </div>
        </template>
    </Dialog>
</template>

<style scoped>
.merge-concept-pair-summary {
    flex: none;
    padding-bottom: 1rem;
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
}

.merge-stepper {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    gap: 1rem;
}

.merge-stepper :deep(.p-steplist) {
    flex: none;
    padding: 0 0 1rem 0;
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
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
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-normal);
    white-space: nowrap;
}

.merge-stepper :deep(.p-step-active) .p-step-title {
    font-weight: var(--p-lingo-font-weight-semibold);
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

.merge-step-body--fill {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding-inline-end: 0;
}

.merge-step-intro {
    margin: 0 0 0.75rem 0;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
}

/* A class on the button itself, since a :deep() rule reaching into the dialog
   loses to PrimeVue's own without !important. */
.footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
}

.footer-button {
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
}

.merge-spinner {
    width: 2.5rem;
    height: 2.5rem;
}
</style>
