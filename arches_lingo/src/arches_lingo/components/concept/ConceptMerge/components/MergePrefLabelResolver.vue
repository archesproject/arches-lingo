<script setup lang="ts">
import { useGettext } from "vue3-gettext";
import Message from "primevue/message";
import RadioButton from "primevue/radiobutton";

import { WARN } from "@/arches_lingo/constants.ts";

import type { PrefLabelConflict } from "@/arches_lingo/components/concept/ConceptMerge/types.ts";

const { conflicts, winnerByLanguage } = defineProps<{
    conflicts: PrefLabelConflict[];
    winnerByLanguage: Record<string, string>;
}>();

const emit = defineEmits<{
    (event: "update:winner", languageCode: string, tileId: string): void;
}>();

const { $gettext } = useGettext();
</script>

<template>
    <div
        v-if="conflicts.length"
        class="pref-label-resolver"
    >
        <Message
            :severity="WARN"
            :closable="false"
        >
            {{
                $gettext(
                    "Only one preferred label per language is allowed. Choose which label stays preferred; the others become alternative labels.",
                )
            }}
        </Message>

        <div
            v-for="conflict in conflicts"
            :key="conflict.languageCode"
            class="pref-label-conflict"
        >
            <span class="pref-label-language">{{
                conflict.languageLabel
            }}</span>
            <label
                v-for="candidate in conflict.candidates"
                :key="candidate.tileId"
                class="pref-label-option"
                :class="{
                    selected:
                        winnerByLanguage[conflict.languageCode] ===
                        candidate.tileId,
                }"
                :for="`pref-label-${candidate.tileId}`"
            >
                <RadioButton
                    :model-value="winnerByLanguage[conflict.languageCode]"
                    :input-id="`pref-label-${candidate.tileId}`"
                    :name="`pref-label-${conflict.languageCode}`"
                    :value="candidate.tileId"
                    @update:model-value="
                        emit(
                            'update:winner',
                            conflict.languageCode,
                            candidate.tileId,
                        )
                    "
                />
                <span class="pref-label-content">{{ candidate.content }}</span>
                <span class="pref-label-source">
                    {{
                        candidate.isFromSurvivor
                            ? $gettext("on this concept")
                            : $gettext("from the other concept")
                    }}
                </span>
            </label>
        </div>
    </div>
</template>

<style scoped>
.pref-label-resolver {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.pref-label-conflict {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
}

.pref-label-language {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
}

.pref-label-option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.625rem;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.25rem;
    cursor: pointer;
}

.pref-label-option.selected {
    border-color: var(--p-primary-color);
    background-color: var(--p-highlight-background);
}

.pref-label-content {
    font-size: var(--p-lingo-font-size-normal);
    overflow-wrap: anywhere;
}

.pref-label-source {
    margin-inline-start: auto;
    font-size: var(--p-lingo-font-size-xxsmall);
    color: var(--p-text-muted-color);
    white-space: nowrap;
}
</style>
