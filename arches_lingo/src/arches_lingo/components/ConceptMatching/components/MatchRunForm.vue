<script setup lang="ts">
import { computed, ref } from "vue";

import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import MultiSelect from "primevue/multiselect";
import Slider from "primevue/slider";

import { useLocalizedLabel } from "@/arches_lingo/components/ConceptMatching/composables/useLocalizedLabel.ts";
import {
    DEFAULT_SIMILARITY_THRESHOLD,
    MAX_SELECTABLE_SIMILARITY,
    MIN_SELECTABLE_SIMILARITY,
    SCHEME_FILTER_MINIMUM_OPTIONS,
    SIMILARITY_STEP,
} from "@/arches_lingo/components/ConceptMatching/constants.ts";
import { buildSignalList } from "@/arches_lingo/components/ConceptMatching/utils.ts";
import { WARN } from "@/arches_lingo/constants.ts";

import type { ConceptMatchRunRequest, Scheme } from "@/arches_lingo/types.ts";

const { schemes, isStartingRun } = defineProps<{
    schemes: Scheme[];
    isStartingRun: boolean;
}>();

const emit = defineEmits<{
    (event: "run-requested", request: ConceptMatchRunRequest): void;
}>();

const { $gettext } = useGettext();
const { labelOf } = useLocalizedLabel();

const selectedSchemeIds = ref<string[]>([]);
const runName = ref("");
const crossSchemeOnly = ref(false);
const sameLanguageOnly = ref(true);
const compareLabels = ref(true);
const compareUris = ref(true);
const compareSimilarLabels = ref(false);
const similarityThreshold = ref(DEFAULT_SIMILARITY_THRESHOLD);

const schemeOptions = computed(() =>
    schemes.map((scheme) => ({ id: scheme.id, name: labelOf(scheme) })),
);

const hasAnySignal = computed(
    () =>
        compareLabels.value || compareUris.value || compareSimilarLabels.value,
);

const canStartRun = computed(() => !isStartingRun && hasAnySignal.value);

const thresholdLabel = computed(() =>
    $gettext("How similar? (%{threshold})", {
        threshold: similarityThreshold.value.toFixed(2),
    }),
);

function requestRun(): void {
    emit("run-requested", {
        name: runName.value.trim(),
        scheme_ids: selectedSchemeIds.value,
        cross_scheme_only: crossSchemeOnly.value,
        same_language_only: sameLanguageOnly.value,
        similarity_threshold: similarityThreshold.value,
        signals: buildSignalList({
            compareUris: compareUris.value,
            compareLabels: compareLabels.value,
            compareSimilarLabels: compareSimilarLabels.value,
        }),
    });
}
</script>

<template>
    <div class="run-form">
        <div class="field">
            <label
                class="label"
                for="match-scheme"
            >
                {{ $gettext("Schemes") }}
            </label>
            <MultiSelect
                v-model="selectedSchemeIds"
                class="scheme-select"
                input-id="match-scheme"
                option-label="name"
                option-value="id"
                display="chip"
                :options="schemeOptions"
                :placeholder="$gettext('Every scheme')"
                :filter="schemeOptions.length > SCHEME_FILTER_MINIMUM_OPTIONS"
                :show-toggle-all="false"
            />
            <p class="option-note">
                {{
                    $gettext(
                        "Both concepts of a pair must be in one of these, so the search never reaches outside them. Leave empty to search everything.",
                    )
                }}
            </p>
        </div>

        <div class="field">
            <label
                class="label"
                for="match-name"
            >
                {{ $gettext("Name (optional)") }}
            </label>
            <InputText
                id="match-name"
                v-model="runName"
                class="name-input"
                :placeholder="$gettext('For finding this run again later')"
            />
        </div>

        <fieldset class="field">
            <legend class="label">{{ $gettext("Compare") }}</legend>
            <div class="control">
                <label class="option">
                    <Checkbox
                        v-model="compareLabels"
                        input-id="match-labels"
                        :binary="true"
                    />
                    <span>{{ $gettext("Labels that match exactly") }}</span>
                </label>
                <label class="option">
                    <Checkbox
                        v-model="compareUris"
                        input-id="match-uris"
                        :binary="true"
                    />
                    <span>{{ $gettext("Concepts sharing a URI") }}</span>
                </label>
                <label class="option">
                    <Checkbox
                        v-model="compareSimilarLabels"
                        input-id="match-similar"
                        :binary="true"
                    />
                    <span>{{
                        $gettext("Labels that are merely similar")
                    }}</span>
                </label>
            </div>
            <Message
                v-if="compareSimilarLabels"
                class="option-message"
                :severity="WARN"
                :closable="false"
            >
                {{
                    $gettext(
                        "Comparing similar labels runs on the server. How long it takes follows how many labels are in scope, and over a large vocabulary that is tens of minutes rather than seconds. Results appear as they are found, and the search carries on if you leave this page.",
                    )
                }}
            </Message>
        </fieldset>

        <div
            v-if="compareSimilarLabels"
            class="field"
        >
            <label
                id="match-threshold-label"
                class="label"
            >
                {{ thresholdLabel }}
            </label>
            <Slider
                v-model="similarityThreshold"
                class="threshold-slider"
                aria-labelledby="match-threshold-label"
                :min="MIN_SELECTABLE_SIMILARITY"
                :max="MAX_SELECTABLE_SIMILARITY"
                :step="SIMILARITY_STEP"
            />
            <p class="option-note">
                {{
                    $gettext(
                        "Lower finds more pairs and more noise. Below about 0.6 most suggestions are coincidence.",
                    )
                }}
            </p>
        </div>

        <fieldset class="field">
            <legend class="label">{{ $gettext("Narrow the results") }}</legend>
            <div class="control">
                <label class="option">
                    <Checkbox
                        v-model="crossSchemeOnly"
                        input-id="match-cross-scheme"
                        :binary="true"
                    />
                    <span>{{
                        $gettext("Only pairs spanning two schemes")
                    }}</span>
                </label>
                <label class="option">
                    <Checkbox
                        v-model="sameLanguageOnly"
                        input-id="match-same-language"
                        :binary="true"
                    />
                    <span>{{
                        $gettext("Only labels in the same language")
                    }}</span>
                </label>
            </div>
        </fieldset>

        <Button
            class="run-button"
            icon="pi pi-search"
            :label="$gettext('Find matches')"
            :disabled="!canStartRun"
            :loading="isStartingRun"
            @click="requestRun"
        />
    </div>
</template>

<style scoped>
.run-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.run-form .field {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    min-width: 0;
    margin: 0;
    padding: 0;
    border: 0;
}

.field .label {
    display: block;
    margin: 0;
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-header-item-label);
}

/* A legend sits outside the fieldset's flex flow, so it takes no gap. */
.field legend.label {
    padding: 0;
    margin-block-end: 0.5rem;
}

/* A container for a widget, not the widget itself: on a Select this would
   stack its label above its dropdown icon and collapse the label. */
.field .control {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.field .scheme-select,
.field .name-input,
.field .threshold-slider {
    width: 100%;
}

.control .option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    cursor: pointer;
}

.field .option-message {
    font-size: var(--p-lingo-font-size-smallnormal);
}

.field .option-note {
    margin: 0;
    font-size: var(--p-lingo-font-size-xxsmall);
    color: var(--p-text-muted-color);
}

.run-form .run-button {
    align-self: flex-start;
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
}

:deep(.p-select),
:deep(.p-multiselect),
:deep(.p-inputtext) {
    border-radius: 0.125rem;
}
</style>
