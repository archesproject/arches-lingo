<script setup lang="ts">
import { computed, useId } from "vue";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";

import LifecycleStateBadge from "@/arches_lingo/components/generic/LifecycleStateBadge.vue";

import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { getParentLabels, getConceptIcon } from "@/arches_lingo/utils.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

import type { SearchResultItem } from "@/arches_lingo/types.ts";

const {
    searchResult,
    isLink = false,
    positionDescription = "",
} = defineProps<{
    searchResult: { index: number; option: SearchResultItem };
    isLink?: boolean;
    positionDescription?: string;
}>();

const emit = defineEmits<{
    (event: "select", clickEvent: MouseEvent): void;
}>();

const router = useRouter();
const positionDescriptionId = useId();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

const label = computed(
    () =>
        getItemLabel(
            searchResult.option,
            selectedLanguage.value.code,
            systemLanguage.value.code,
        ).value,
);

const conceptHref = computed(
    () =>
        router.resolve({
            name: routeNames.concept,
            params: { id: searchResult.option.id },
        }).href,
);
</script>

<template>
    <div
        class="search-result"
        :class="{ 'is-even': searchResult.index % 2 === 0 }"
    >
        <div style="margin: 0 0.5rem">
            <span class="result-label">
                <i
                    :class="[
                        getConceptIcon(searchResult.option),
                        'concept-icon',
                    ]"
                    aria-hidden="true"
                />
                <a
                    v-if="isLink"
                    class="result-link"
                    :href="conceptHref"
                    :aria-describedby="
                        positionDescription ? positionDescriptionId : undefined
                    "
                    @click="emit('select', $event)"
                >
                    {{ label }}
                </a>
                <template v-else>{{ label }}</template>
                <LifecycleStateBadge
                    :lifecycle-state-id="
                        searchResult.option.resource_instance_lifecycle_state_id
                    "
                    :lifecycle-state-name="
                        searchResult.option
                            .resource_instance_lifecycle_state_name
                    "
                />
            </span>
        </div>

        <span
            v-if="positionDescription"
            :id="positionDescriptionId"
            class="p-hidden-accessible"
        >
            {{ positionDescription }}
        </span>

        <div class="search-result-hierarchy">
            [
            {{
                getParentLabels(
                    searchResult.option,
                    selectedLanguage.code,
                    systemLanguage.code,
                )
            }}
            ]
        </div>
    </div>
</template>

<style scoped>
.search-result {
    position: relative;
    height: 100%;
    width: 100%;
    font-size: 0.875rem;
    padding: 0.5rem;
    display: flex;
    align-items: flex-start;
    flex-direction: column;
    background-color: var(--p-dialog-background);
    border-bottom: 0.0625rem solid var(--p-search-result-border-bottom);
    color: var(--p-search-result-color);
    gap: 0.125rem;
}

.result-label {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    flex-wrap: wrap;
}

.result-link {
    color: inherit;
    text-decoration: none;
}

.result-link::after {
    content: "";
    position: absolute;
    inset: 0;
}

.result-link:focus-visible {
    outline: none;
}

.result-link:focus-visible::after {
    outline: 0.125rem solid var(--p-focus-ring-color);
    outline-offset: -0.125rem;
}

.search-result-hierarchy {
    margin: 0 0.5rem;
    font-size: var(--p-lingo-font-size-xsmall);
    color: var(--p-search-result-hierarchy-color);
}

.is-even {
    background-color: var(--p-search-result-is-even-background);
}

.search-result:has(.result-link):hover,
.search-result:focus-within {
    background-color: var(--p-search-result-focus-background);
}

.concept-icon {
    font-size: var(--p-lingo-font-size-xxsmall);
}
</style>
