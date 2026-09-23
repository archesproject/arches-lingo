<script setup lang="ts">
import { computed, ref } from "vue";

import { useGettext } from "vue3-gettext";
import { storeToRefs } from "pinia";

import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import MultiSelect from "primevue/multiselect";
import Slider from "primevue/slider";

import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

import { DEFAULT_SIMILARITY_THRESHOLD } from "@/arches_lingo/components/concept-matching/constants.ts";
import { WARN } from "@/arches_lingo/constants.ts";
import {
    buildSignalList,
    describeExpectedDuration,
    labelsInScope,
} from "@/arches_lingo/components/concept-matching/utils.ts";

import type {
    ConceptMatchRunRequest,
    ConceptMatchScopeSizes,
    Scheme,
} from "@/arches_lingo/types.ts";

const {
    schemes,
    isRunning,
    scopeSizes = null,
} = defineProps<{
    schemes: Scheme[];
    isRunning: boolean;
    scopeSizes?: ConceptMatchScopeSizes | null;
}>();

const emit = defineEmits<{
    (event: "run", request: ConceptMatchRunRequest): void;
}>();

const { $gettext } = useGettext();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

// Schemes carry labels rather than a name, so they are named the way every
// other scheme in the interface is.
const schemeOptions = computed(function () {
    return schemes.map((scheme) => ({
        id: scheme.id,
        name: getItemLabel(
            scheme,
            selectedLanguage.value.code,
            systemLanguage.value.code,
        ).value,
    }));
});

const selectedSchemeIds = ref<string[]>([]);
const runName = ref("");

// Comparing similar labels is one index probe per label, so what it costs
// follows how much of the vocabulary is in scope. Naming a handful of schemes
// is not the same as a small search: over a large vocabulary a whole-corpus run
// has measured in the tens of minutes, and a scope holding most of that
// vocabulary takes very nearly as long.
const expectedDurationText = computed(function () {
    // Without the sizes there is nothing to count, so the warning says the one
    // thing true of every corpus rather than guessing at a figure.
    if (!scopeSizes) {
        return $gettext(
            "Comparing similar labels runs on the server. How long it takes follows how many labels are in scope, and over a large vocabulary that is tens of minutes rather than seconds. Results appear as they are found, and the search carries on if you leave this page.",
        );
    }

    const labelCount = labelsInScope(
        selectedSchemeIds.value,
        scopeSizes.total_labels,
        scopeSizes.labels_by_scheme,
    );
    return $gettext(
        "Comparing %{labels} labels of %{total} in the vocabulary. This runs on the server and should take %{duration}. Results appear as they are found, and the search carries on if you leave this page.",
        {
            labels: labelCount.toLocaleString(),
            total: scopeSizes.total_labels.toLocaleString(),
            duration: describeExpectedDuration(labelCount, $gettext),
        },
    );
});
const crossSchemeOnly = ref(false);
const sameLanguageOnly = ref(true);
const compareLabels = ref(true);
const compareUris = ref(true);
const compareSimilarLabels = ref(false);
const similarityThreshold = ref(DEFAULT_SIMILARITY_THRESHOLD);

function onRun() {
    const signals = buildSignalList({
        compareUris: compareUris.value,
        compareLabels: compareLabels.value,
        compareSimilarLabels: compareSimilarLabels.value,
    });

    emit("run", {
        name: runName.value.trim(),
        scheme_ids: selectedSchemeIds.value,
        cross_scheme_only: crossSchemeOnly.value,
        same_language_only: sameLanguageOnly.value,
        similarity_threshold: similarityThreshold.value,
        signals,
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
                input-id="match-scheme"
                :options="schemeOptions"
                option-label="name"
                option-value="id"
                :placeholder="$gettext('Every scheme')"
                :filter="schemeOptions.length > 8"
                :show-toggle-all="false"
                display="chip"
                class="scheme-select"
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
                :placeholder="$gettext('For finding this run again later')"
                class="name-input"
            />
        </div>

        <div class="field">
            <span class="label">{{ $gettext("Compare") }}</span>
            <div class="control">
                <label class="option">
                    <Checkbox
                        v-model="compareLabels"
                        :binary="true"
                        input-id="match-labels"
                    />
                    <span>{{ $gettext("Labels that match exactly") }}</span>
                </label>
                <label class="option">
                    <Checkbox
                        v-model="compareUris"
                        :binary="true"
                        input-id="match-uris"
                    />
                    <span>{{ $gettext("Concepts sharing a URI") }}</span>
                </label>
                <label class="option">
                    <Checkbox
                        v-model="compareSimilarLabels"
                        :binary="true"
                        input-id="match-similar"
                    />
                    <span>{{
                        $gettext("Labels that are merely similar")
                    }}</span>
                </label>
            </div>
            <Message
                v-if="compareSimilarLabels"
                :severity="WARN"
                :closable="false"
                class="option-message"
            >
                {{ expectedDurationText }}
            </Message>
        </div>

        <div
            v-if="compareSimilarLabels"
            class="field"
        >
            <label
                class="label"
                for="match-threshold"
            >
                {{
                    $gettext("How similar? (%{threshold})", {
                        threshold: similarityThreshold.toFixed(2),
                    })
                }}
            </label>
            <Slider
                v-model="similarityThreshold"
                input-id="match-threshold"
                :min="0.4"
                :max="0.95"
                :step="0.05"
                class="threshold-slider"
            />
            <p class="option-note">
                {{
                    $gettext(
                        "Lower finds more pairs and more noise. Below about 0.6 most suggestions are coincidence.",
                    )
                }}
            </p>
        </div>

        <div class="field">
            <span class="label">{{ $gettext("Narrow the results") }}</span>
            <div class="control">
                <label class="option">
                    <Checkbox
                        v-model="crossSchemeOnly"
                        :binary="true"
                        input-id="match-cross-scheme"
                    />
                    <span>{{
                        $gettext("Only pairs spanning two schemes")
                    }}</span>
                </label>
                <label class="option">
                    <Checkbox
                        v-model="sameLanguageOnly"
                        :binary="true"
                        input-id="match-same-language"
                    />
                    <span>{{
                        $gettext("Only labels in the same language")
                    }}</span>
                </label>
            </div>
        </div>

        <Button
            icon="pi pi-search"
            :label="$gettext('Find matches')"
            class="run-button"
            :disabled="
                isRunning ||
                (!compareLabels && !compareUris && !compareSimilarLabels)
            "
            :loading="isRunning"
            @click="onRun"
        />
    </div>
</template>

<style scoped>
.run-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.field {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.label {
    display: block;
    margin: 0;
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-header-item-label);
}

/* A container for a widget, not the widget itself: putting this on a Select
   would stack its label above its dropdown icon and collapse the label. */
.control {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.scheme-select,
.name-input,
.threshold-slider {
    width: 100%;
}

.option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    cursor: pointer;
}

.option-message {
    font-size: var(--p-lingo-font-size-smallnormal);
}

.option-note {
    margin: 0;
    font-size: var(--p-lingo-font-size-xxsmall);
    color: var(--p-inputtext-placeholder-color);
}

.run-button {
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
