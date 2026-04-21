import { ref } from "vue";
import { defineStore } from "pinia";

import { fetchConceptSets } from "@/arches_lingo/api.ts";

import type { ConceptSetItem } from "@/arches_lingo/types.ts";

export const useConceptSetStore = defineStore("conceptSets", () => {
    const conceptSets = ref<ConceptSetItem[]>([]);

    async function loadConceptSets() {
        const result = await fetchConceptSets();
        conceptSets.value = result.data;
    }

    return { conceptSets, loadConceptSets };
});
