<script setup lang="ts">
import { computed } from "vue";

import { useGettext } from "vue3-gettext";
import Checkbox from "primevue/checkbox";
import Message from "primevue/message";

import MergeRetirementOptions from "@/arches_lingo/components/concept/ConceptMerge/components/MergeRetirementOptions.vue";

import { INFO, WARN } from "@/arches_lingo/constants.ts";

import type { MergeRetirementStrategy } from "@/arches_lingo/types.ts";
import type { MergeSectionSummary } from "@/arches_lingo/components/concept/ConceptMerge/types.ts";

const {
    survivorLabel,
    absorbedLabel,
    sectionSummaries,
    isCrossScheme,
    isAbsorbedDraft,
    removeAbsorbedConcept,
} = defineProps<{
    absorbedConceptId: string;
    survivorConceptId: string;
    survivorLabel: string | undefined;
    absorbedLabel: string | undefined;
    sectionSummaries: MergeSectionSummary[];
    createExactMatchTiles: boolean;
    removeAbsorbedConcept: boolean;
    retirementStrategy: MergeRetirementStrategy;
    isCrossScheme: boolean;
    isAbsorbedDraft: boolean;
}>();

const emit = defineEmits<{
    (event: "update:createExactMatchTiles", value: boolean): void;
    (event: "update:removeAbsorbedConcept", value: boolean): void;
    (
        event: "update:retirementStrategy",
        strategy: MergeRetirementStrategy,
    ): void;
}>();

const { $gettext } = useGettext();

const summaryText = computed(function () {
    const names = {
        absorbed: absorbedLabel ?? "",
        survivor: survivorLabel ?? "",
    };
    if (isCrossScheme) {
        return $gettext(
            'Copying values from "%{absorbed}" into "%{survivor}".',
            names,
        );
    }
    return $gettext('Merging "%{absorbed}" into "%{survivor}".', names);
});

const hasSelections = computed(function () {
    return sectionSummaries.length > 0;
});

const irreversibilityWarning = computed(function () {
    if (isAbsorbedDraft && removeAbsorbedConcept) {
        return $gettext(
            'Merges cannot be undone. Copied values become new values on the surviving concept, and "%{absorbed}" is permanently deleted.',
            { absorbed: absorbedLabel ?? "" },
        );
    }
    return $gettext(
        "Merges cannot be undone. Copied values become new values on the surviving concept.",
    );
});

const removalTitle = computed(function () {
    const names = { absorbed: absorbedLabel ?? "" };
    if (isAbsorbedDraft) {
        return $gettext('Delete "%{absorbed}" afterwards', names);
    }
    return $gettext('Retire "%{absorbed}" afterwards', names);
});

const removalDescription = computed(function () {
    if (isAbsorbedDraft) {
        return $gettext(
            "It is a draft that has never been published, so it is permanently deleted along with its values. Deletion happens as part of the merge, so either both land or neither does.",
        );
    }
    return $gettext(
        "Retirement happens as part of the merge, so either both land or neither does.",
    );
});
</script>

<template>
    <div class="merge-confirmation">
        <p class="merge-confirmation-summary">{{ summaryText }}</p>

        <Message
            v-if="!hasSelections"
            :severity="INFO"
            :closable="false"
        >
            {{
                $gettext(
                    "No values were selected. The merge will only record the link between the two concepts.",
                )
            }}
        </Message>

        <ul
            v-else
            class="merge-confirmation-list"
        >
            <li
                v-for="summary in sectionSummaries"
                :key="summary.sectionTitle"
            >
                <span class="merge-confirmation-count">{{
                    summary.selectedCount
                }}</span>
                {{ summary.sectionTitle }}
            </li>
        </ul>

        <Message
            v-if="isAbsorbedDraft"
            :severity="INFO"
            :closable="false"
        >
            {{
                $gettext(
                    '"%{absorbed}" is a draft and has no URI yet, so no exactMatch is recorded.',
                    { absorbed: absorbedLabel ?? "" },
                )
            }}
        </Message>

        <label
            v-else
            class="merge-confirmation-option"
            for="merge-exact-match"
        >
            <Checkbox
                :model-value="createExactMatchTiles"
                input-id="merge-exact-match"
                :binary="true"
                @update:model-value="
                    emit('update:createExactMatchTiles', $event as boolean)
                "
            />
            <span class="merge-confirmation-option-body">
                <span>{{
                    $gettext("Record an exactMatch between the two")
                }}</span>
                <span class="merge-confirmation-option-desc">
                    {{
                        $gettext(
                            "Keeps the merged-away concept's URI meaningful to anyone who resolves it later.",
                        )
                    }}
                </span>
            </span>
        </label>

        <Message
            v-if="isCrossScheme"
            :severity="INFO"
            :closable="false"
        >
            {{
                $gettext(
                    'The two concepts are in different schemes, so "%{absorbed}" stays where it is and is left unchanged. Retiring or deleting it is only offered for a merge within one scheme.',
                    { absorbed: absorbedLabel ?? "" },
                )
            }}
        </Message>

        <label
            v-if="!isCrossScheme"
            class="merge-confirmation-option"
            for="merge-remove"
        >
            <Checkbox
                :model-value="removeAbsorbedConcept"
                input-id="merge-remove"
                :binary="true"
                @update:model-value="
                    emit('update:removeAbsorbedConcept', $event as boolean)
                "
            />
            <span class="merge-confirmation-option-body">
                <span>{{ removalTitle }}</span>
                <span class="merge-confirmation-option-desc">
                    {{ removalDescription }}
                </span>
            </span>
        </label>

        <MergeRetirementOptions
            v-if="!isCrossScheme && removeAbsorbedConcept"
            :absorbed-concept-id="absorbedConceptId"
            :survivor-concept-id="survivorConceptId"
            :absorbed-label="absorbedLabel"
            :survivor-label="survivorLabel"
            :retirement-strategy="retirementStrategy"
            :is-deletion="isAbsorbedDraft"
            @update:retirement-strategy="
                emit('update:retirementStrategy', $event)
            "
        />

        <Message
            :severity="WARN"
            :closable="false"
        >
            {{ irreversibilityWarning }}
        </Message>
    </div>
</template>

<style scoped>
.merge-confirmation {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.merge-confirmation-summary {
    margin: 0;
    font-size: var(--p-lingo-font-size-normal);
}

.merge-confirmation-list {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    margin: 0;
    padding: 0;
    list-style: none;
    font-size: var(--p-lingo-font-size-smallnormal);
}

.merge-confirmation-count {
    display: inline-block;
    min-width: 1.5rem;
    font-weight: var(--p-lingo-font-weight-bold);
}

.merge-confirmation-option {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.625rem;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.125rem;
    cursor: pointer;
}

.merge-confirmation-option-body {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    min-width: 0;
}

.merge-confirmation-option-desc {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
}
</style>
