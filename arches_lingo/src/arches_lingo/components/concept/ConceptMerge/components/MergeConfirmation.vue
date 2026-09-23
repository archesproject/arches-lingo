<script setup lang="ts">
import { computed } from "vue";

import { useGettext } from "vue3-gettext";
import Checkbox from "primevue/checkbox";
import Message from "primevue/message";

import { INFO, WARN } from "@/arches_lingo/constants.ts";

import MergeRetirementOptions from "@/arches_lingo/components/concept/ConceptMerge/components/MergeRetirementOptions.vue";

import type { MergeRetirementStrategy } from "@/arches_lingo/types.ts";
import type { MergeSectionSummary } from "@/arches_lingo/components/concept/ConceptMerge/types.ts";

const { survivorLabel, absorbedLabel, sectionSummaries, isCrossScheme } =
    defineProps<{
        absorbedConceptId: string;
        survivorLabel: string | undefined;
        absorbedLabel: string | undefined;
        sectionSummaries: MergeSectionSummary[];
        createExactMatchTiles: boolean;
        retireAbsorbedConcept: boolean;
        retirementStrategy: MergeRetirementStrategy;
        isCrossScheme: boolean;
    }>();

const emit = defineEmits<{
    (event: "update:createExactMatchTiles", value: boolean): void;
    (event: "update:retireAbsorbedConcept", value: boolean): void;
    (
        event: "update:retirementStrategy",
        strategy: MergeRetirementStrategy,
    ): void;
}>();

const { $gettext } = useGettext();

const summaryText = computed(function () {
    return $gettext('Merging "%{absorbed}" into "%{survivor}".', {
        absorbed: absorbedLabel ?? "",
        survivor: survivorLabel ?? "",
    });
});

const hasSelections = computed(function () {
    return sectionSummaries.length > 0;
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

        <label
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
                    'The two concepts are in different schemes, so "%{absorbed}" stays where it is. Retiring it is only offered for a merge within one scheme.',
                    { absorbed: absorbedLabel ?? "" },
                )
            }}
        </Message>

        <label
            v-if="!isCrossScheme"
            class="merge-confirmation-option"
            for="merge-retire"
        >
            <Checkbox
                :model-value="retireAbsorbedConcept"
                input-id="merge-retire"
                :binary="true"
                @update:model-value="
                    emit('update:retireAbsorbedConcept', $event as boolean)
                "
            />
            <span class="merge-confirmation-option-body">
                <span>
                    {{
                        $gettext('Retire "%{absorbed}" afterwards', {
                            absorbed: absorbedLabel ?? "",
                        })
                    }}
                </span>
                <span class="merge-confirmation-option-desc">
                    {{
                        $gettext(
                            "Retirement happens as part of the merge, so either both land or neither does.",
                        )
                    }}
                </span>
            </span>
        </label>

        <MergeRetirementOptions
            v-if="!isCrossScheme && retireAbsorbedConcept"
            :absorbed-concept-id="absorbedConceptId"
            :absorbed-label="absorbedLabel"
            :survivor-label="survivorLabel"
            :retirement-strategy="retirementStrategy"
            @update:retirement-strategy="
                emit('update:retirementStrategy', $event)
            "
        />

        <Message
            :severity="WARN"
            :closable="false"
        >
            {{
                $gettext(
                    "Merges cannot be undone. Copied values become new values on the surviving concept.",
                )
            }}
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
