<script setup lang="ts">
import { computed, nextTick, onMounted, ref, useId, watch } from "vue";

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
import { useMediaQuery } from "@/arches_lingo/composables/useMediaQuery.ts";
import { focusWithoutScrolling } from "@/arches_lingo/utils.ts";
import {
    DANGER,
    DRAFT_LIFECYCLE_STATE_ID,
    ERROR,
    SECONDARY,
    SHORT_VIEWPORT_MEDIA_QUERY,
    STRATEGY_REPARENT_TO_SURVIVOR,
} from "@/arches_lingo/constants.ts";
import {
    MERGE_DIALOG_FRAME_PASS_THROUGH,
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
    ...MERGE_DIALOG_FRAME_PASS_THROUGH,
    content: {
        style: {
            display: "flex",
            flexDirection: "column",
            flex: "1",
            minHeight: "0",
            overflow: "hidden",
            padding: "1.25rem",
            paddingBlockStart: "1rem",
        },
    },
};

const MERGE_STEP_ORDER = [
    MERGE_STEP_SELECT,
    MERGE_STEP_COMPARE,
    MERGE_STEP_CONFIRM,
];

const PRESELECTED_MERGE_STEP_ORDER = [MERGE_STEP_COMPARE, MERGE_STEP_CONFIRM];

const SHORT_VIEWPORT_DIALOG_PASS_THROUGH = {
    ...DIALOG_PASS_THROUGH,
    content: {
        style: { ...DIALOG_PASS_THROUGH.content.style, overflow: "auto" },
    },
};

const {
    survivorConcept,
    survivorLabel,
    schemeId,
    graphSlug,
    preselectedConceptId = undefined,
} = defineProps<{
    visible: boolean;
    survivorConcept: ResourceInstanceResult;
    survivorLabel: string | undefined;
    schemeId: string;
    graphSlug: string;
    // Skips the picker, e.g. when match review already knows the pair.
    preselectedConceptId?: string;
}>();

const emit = defineEmits<{
    cancel: [];
    merged: [];
    "after-hide": [];
}>();

const { $gettext } = useGettext();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());
const isShortViewport = useMediaQuery(SHORT_VIEWPORT_MEDIA_QUERY);
const stepHeadingIdPrefix = useId();

const currentStep = ref(
    preselectedConceptId ? MERGE_STEP_COMPARE : MERGE_STEP_SELECT,
);
const survivorSearchResult = ref<SearchResultItem>();
const selectedConcept = ref<SearchResultItem>();
const absorbedConcept = ref<ResourceInstanceResult>();
const mergePreview = ref<ConceptMergePreview>();
const isLoadingAbsorbedConcept = ref(false);
const fetchError = ref<string | null>(null);
const createExactMatchTiles = ref(true);
const removeAbsorbedConcept = ref(true);
const retirementStrategy = ref<MergeRetirementStrategy>(
    STRATEGY_REPARENT_TO_SURVIVOR,
);
const selectionState = ref<MergeSelectionState>();
const isMerging = ref(false);
const mergeError = ref<string | null>(null);

const mergeStepOrder = computed(function () {
    if (preselectedConceptId) {
        return PRESELECTED_MERGE_STEP_ORDER;
    }
    return MERGE_STEP_ORDER;
});

const isOnFirstStep = computed(function () {
    return currentStep.value === mergeStepOrder.value[0];
});

const isOnConfirmStep = computed(function () {
    return currentStep.value === MERGE_STEP_CONFIRM;
});

const stepTitles = computed<Record<number, string>>(function () {
    return {
        [MERGE_STEP_SELECT]: $gettext("Choose concept"),
        [MERGE_STEP_COMPARE]: $gettext("Choose values"),
        [MERGE_STEP_CONFIRM]: $gettext("Confirm"),
    };
});

const backButton = computed(function () {
    if (isOnFirstStep.value) {
        return {
            label: $gettext("Cancel"),
            icon: "pi pi-times",
            severity: DANGER,
            isOutlined: false,
        };
    }
    return {
        label: $gettext("Back"),
        icon: "pi pi-arrow-left",
        severity: SECONDARY,
        isOutlined: true,
    };
});

const forwardButton = computed(function () {
    if (isOnConfirmStep.value) {
        return {
            label: $gettext("Merge"),
            icon: isMerging.value ? "pi pi-spin pi-spinner" : "pi pi-check",
            iconPosition: "left" as const,
            isDisabled: !canConfirm.value,
        };
    }
    return {
        label: $gettext("Next"),
        icon: "pi pi-arrow-right",
        iconPosition: "right" as const,
        isDisabled: isNextDisabled.value,
    };
});

const previousStep = computed(function () {
    const stepIndex = mergeStepOrder.value.indexOf(currentStep.value);
    return mergeStepOrder.value[Math.max(stepIndex - 1, 0)];
});

const nextStep = computed(function () {
    const stepIndex = mergeStepOrder.value.indexOf(currentStep.value);
    return mergeStepOrder.value[
        Math.min(stepIndex + 1, mergeStepOrder.value.length - 1)
    ];
});

const isCrossScheme = computed(function () {
    return mergePreview.value?.is_cross_scheme ?? false;
});

const isAbsorbedDraft = computed(function () {
    return (
        selectedConcept.value?.resource_instance_lifecycle_state_id ===
        DRAFT_LIFECYCLE_STATE_ID
    );
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

watch(
    () => preselectedConceptId,
    function (conceptId) {
        if (conceptId) {
            loadPreselectedConcept(conceptId);
        }
    },
    { immediate: true },
);

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

async function loadPreselectedConcept(conceptId: string): Promise<void> {
    isLoadingAbsorbedConcept.value = true;
    try {
        const ancestorPaths: SearchResultHierarchy[] =
            await fetchConceptAncestorPaths(conceptId);
        const searchResult = buildSearchResultFromAncestorPath(
            ancestorPaths[0]?.searchResults ?? [],
        );
        if (!searchResult) {
            throw new Error(
                $gettext("The concept to merge could not be found."),
            );
        }
        await onConceptSelected(searchResult);
    } catch (error) {
        fetchError.value =
            error instanceof Error ? error.message : String(error);
        isLoadingAbsorbedConcept.value = false;
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

function getStepHeadingId(step: number) {
    return `${stepHeadingIdPrefix}-${step}`;
}

function getStepHeadingText(step: number) {
    return $gettext("Step %{number} of %{total}: %{title}", {
        number: String(mergeStepOrder.value.indexOf(step) + 1),
        total: String(mergeStepOrder.value.length),
        title: stepTitles.value[step],
    });
}

async function goToStep(step: number) {
    currentStep.value = step;
    await nextTick();
    const stepHeading = document.getElementById(getStepHeadingId(step));
    if (stepHeading) {
        focusWithoutScrolling(stepHeading);
    }
}

function onBackButtonClick() {
    if (isOnFirstStep.value) {
        emit("cancel");
    } else {
        goToStep(previousStep.value);
    }
}

// Disabling the focused Merge button would drop focus, so clicks are ignored instead.
function onForwardButtonClick() {
    if (isOnConfirmStep.value) {
        if (!isMerging.value) {
            onMergeConfirmed();
        }
    } else {
        goToStep(nextStep.value);
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
                    removeAbsorbedConcept: removeAbsorbedConcept.value,
                    retirementStrategy: retirementStrategy.value,
                },
                isCrossScheme.value,
                isAbsorbedDraft.value,
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
        :visible="visible"
        :modal="true"
        :header="$gettext('Merge Concepts')"
        class="concept-merge-dialog"
        :closable="!isMerging"
        :style="DIALOG_SIZE"
        :pt="
            isShortViewport
                ? SHORT_VIEWPORT_DIALOG_PASS_THROUGH
                : DIALOG_PASS_THROUGH
        "
        @update:visible="onVisibleChange"
        @after-hide="emit('after-hide')"
    >
        <Stepper
            v-model:value="currentStep"
            class="merge-stepper"
        >
            <StepList>
                <Step
                    v-if="!preselectedConceptId"
                    :value="MERGE_STEP_SELECT"
                >
                    {{ stepTitles[MERGE_STEP_SELECT] }}
                </Step>
                <Step
                    :value="MERGE_STEP_COMPARE"
                    :disabled="!canCompare"
                >
                    {{ stepTitles[MERGE_STEP_COMPARE] }}
                </Step>
                <Step
                    :value="MERGE_STEP_CONFIRM"
                    :disabled="!canConfirm"
                >
                    {{ stepTitles[MERGE_STEP_CONFIRM] }}
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
                <StepPanel
                    v-if="!preselectedConceptId"
                    :value="MERGE_STEP_SELECT"
                >
                    <div class="merge-step">
                        <h2
                            :id="getStepHeadingId(MERGE_STEP_SELECT)"
                            class="p-hidden-accessible"
                        >
                            {{ getStepHeadingText(MERGE_STEP_SELECT) }}
                        </h2>
                        <div class="merge-step-body merge-step-body--fill">
                            <p class="merge-step-intro">
                                {{
                                    $gettext(
                                        'Choose the concept to merge into "%{name}". "%{name}" stays, the values you pick are copied onto it, and within the same scheme the other concept can be retired (or, if it is a draft, deleted) afterwards.',
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
                        <h2
                            :id="getStepHeadingId(MERGE_STEP_COMPARE)"
                            class="p-hidden-accessible"
                        >
                            {{ getStepHeadingText(MERGE_STEP_COMPARE) }}
                        </h2>
                        <div class="merge-step-body">
                            <ProgressSpinner
                                v-if="isLoadingAbsorbedConcept"
                                class="merge-spinner"
                            />
                            <Message
                                v-else-if="fetchError"
                                :severity="ERROR"
                                :closable="false"
                            >
                                <span>{{ fetchError }}</span>
                            </Message>
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
                        <h2
                            :id="getStepHeadingId(MERGE_STEP_CONFIRM)"
                            class="p-hidden-accessible"
                        >
                            {{ getStepHeadingText(MERGE_STEP_CONFIRM) }}
                        </h2>
                        <div class="merge-step-body">
                            <MergeConfirmation
                                v-if="absorbedConcept"
                                v-model:create-exact-match-tiles="
                                    createExactMatchTiles
                                "
                                v-model:remove-absorbed-concept="
                                    removeAbsorbedConcept
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
                                :is-absorbed-draft="isAbsorbedDraft"
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
                    :icon="backButton.icon"
                    :label="backButton.label"
                    :severity="backButton.severity"
                    :outlined="backButton.isOutlined"
                    :disabled="isMerging"
                    class="footer-button"
                    @click="onBackButtonClick"
                />
                <Button
                    :icon="forwardButton.icon"
                    :icon-pos="forwardButton.iconPosition"
                    :label="forwardButton.label"
                    :disabled="forwardButton.isDisabled"
                    :aria-disabled="isMerging"
                    class="footer-button"
                    @click="onForwardButtonClick"
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

/* PrimeVue draws a Message's border as an outline outside its box, which this
   scrolling container would otherwise clip. */
.merge-step-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding-block: var(--p-message-border-width);
    padding-inline-start: var(--p-message-border-width);
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

@media (max-height: 40rem) {
    .merge-stepper,
    .merge-stepper :deep(.p-steppanels),
    .merge-stepper :deep(.p-steppanel),
    .merge-step,
    .merge-step-body {
        flex: none;
        height: auto;
        min-height: auto;
    }

    .merge-step-body,
    .merge-step-body--fill {
        overflow: visible;
    }
}
</style>
