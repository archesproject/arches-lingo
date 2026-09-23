<script setup lang="ts">
import { onMounted, ref, watch } from "vue";

import { useGettext } from "vue3-gettext";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";

import { fetchConceptMergeHistory } from "@/arches_lingo/api.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { useResourceStore } from "@/arches_lingo/composables/useResourceStore.ts";

import type { ConceptMergeHistoryEntry } from "@/arches_lingo/types.ts";

const { resourceInstanceId } = defineProps<{
    resourceInstanceId: string;
}>();

const { $gettext } = useGettext();
const router = useRouter();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());
const resourceStore = useResourceStore();

const merges = ref<ConceptMergeHistoryEntry[]>([]);

function entryText(entry: ConceptMergeHistoryEntry) {
    const counterpartName =
        getItemLabel(
            { labels: entry.counterpart_concept_labels },
            selectedLanguage.value.code,
            systemLanguage.value.code,
        ).value || $gettext("a deleted concept");

    if (entry.direction === "absorbed") {
        return $gettext("Merged from %{name}", { name: counterpartName });
    }
    return $gettext("Merged into %{name}", { name: counterpartName });
}

function openCounterpart(entry: ConceptMergeHistoryEntry) {
    router.push({
        name: routeNames.concept,
        params: { id: entry.counterpart_concept_id },
    });
}

// A failed lookup should never block the header from rendering.
async function loadMergeHistory() {
    try {
        merges.value = await fetchConceptMergeHistory(resourceInstanceId);
    } catch {
        merges.value = [];
    }
}

onMounted(loadMergeHistory);

// A merge performed from this page adds an entry, so the history has to follow
// the resource rather than only loading once.
watch(() => resourceStore.resource.value, loadMergeHistory);
</script>

<template>
    <ul
        v-if="merges.length"
        class="concept-merge-history"
    >
        <li
            v-for="entry in merges"
            :key="entry.id"
        >
            <i class="pi pi-sign-in"></i>
            <button
                type="button"
                class="concept-merge-link"
                @click="openCounterpart(entry)"
            >
                {{ entryText(entry) }}
            </button>
        </li>
    </ul>
</template>

<style scoped>
.concept-merge-history {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin: 0;
    padding: 0;
    list-style: none;
}

.concept-merge-history li {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
}

.concept-merge-link {
    padding: 0;
    border: none;
    background: none;
    color: var(--p-primary-color);
    font-size: inherit;
    cursor: pointer;
    text-decoration: underline;
}
</style>
