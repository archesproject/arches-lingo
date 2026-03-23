import { ref } from "vue";
import { defineStore } from "pinia";

import { fetchConcepts } from "@/arches_lingo/api.ts";

import type { Concept, ConceptPathNode, Scheme } from "@/arches_lingo/types.ts";

function searchConcepts(
    concepts: Concept[],
    conceptId: string,
): Concept | null {
    for (const concept of concepts) {
        if (concept.id === conceptId) return concept;
        const found = searchConcepts(concept.narrower, conceptId);
        if (found !== null) return found;
    }
    return null;
}

function searchParentPaths(
    concepts: Concept[],
    conceptId: string,
    currentPath: ConceptPathNode[],
    results: ConceptPathNode[][],
): void {
    for (const concept of concepts) {
        currentPath.push({
            id: concept.id,
            labels: concept.labels,
            guide_term: concept.guide_term,
            top_concept: concept.top_concept,
        });
        if (concept.id === conceptId) {
            results.push([...currentPath]);
        } else {
            searchParentPaths(
                concept.narrower,
                conceptId,
                currentPath,
                results,
            );
        }
        currentPath.pop();
    }
}

export const useConceptStore = defineStore("concepts", () => {
    const schemes = ref<Scheme[]>([]);
    const isLoading = ref(false);
    const error = ref<Error | null>(null);

    let inflightRefresh: Promise<void> | null = null;

    async function initialize() {
        if (inflightRefresh) return inflightRefresh;
        if (schemes.value.length > 0) return;
        return refresh();
    }

    async function refresh() {
        const fetchPromise = (async () => {
            isLoading.value = true;
            error.value = null;
            try {
                const data = await fetchConcepts();
                schemes.value = data.schemes as Scheme[];
            } catch (err) {
                error.value =
                    err instanceof Error ? err : new Error(String(err));
                throw err;
            } finally {
                isLoading.value = false;
                inflightRefresh = null;
            }
        })();
        inflightRefresh = fetchPromise;
        return fetchPromise;
    }

    function findConcept(conceptId: string): Concept | null {
        for (const scheme of schemes.value) {
            const found = searchConcepts(scheme.top_concepts, conceptId);
            if (found !== null) return found;
        }
        return null;
    }

    function getNarrower(conceptId: string): Concept[] {
        return findConcept(conceptId)?.narrower ?? [];
    }

    function getParentPaths(conceptId: string): ConceptPathNode[][] {
        const results: ConceptPathNode[][] = [];
        const currentPath: ConceptPathNode[] = [];

        for (const scheme of schemes.value) {
            currentPath.push({ id: scheme.id, labels: scheme.labels });
            searchParentPaths(
                scheme.top_concepts,
                conceptId,
                currentPath,
                results,
            );
            currentPath.pop();
        }

        return results;
    }

    return {
        schemes,
        isLoading,
        error,
        initialize,
        refresh,
        getNarrower,
        findConcept,
        getParentPaths,
    };
});
