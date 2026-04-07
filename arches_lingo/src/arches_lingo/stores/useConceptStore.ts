import { ref } from "vue";
import { defineStore } from "pinia";

import { fetchConcepts, fetchConceptChildren } from "@/arches_lingo/api.ts";

import type { Concept, ConceptPathNode, Scheme } from "@/arches_lingo/types.ts";

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

    // Flat lookup map for O(1) concept access without recursive search.
    const conceptsById = ref<Map<string, Concept>>(new Map());

    // Track in-flight child fetch requests to avoid duplicate requests.
    const inflightChildFetches = new Map<string, Promise<Concept[]>>();

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
                const fetchedSchemes = data.schemes as Scheme[];
                // Initialize every shallow concept with an empty narrower array
                // so consumers can always rely on concept.narrower being an array.
                for (const scheme of fetchedSchemes) {
                    for (const topConcept of scheme.top_concepts) {
                        topConcept.narrower = topConcept.narrower ?? [];
                        conceptsById.value.set(topConcept.id, topConcept);
                    }
                }
                schemes.value = fetchedSchemes;
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

    async function loadChildren(conceptId: string): Promise<Concept[]> {
        const existing = conceptsById.value.get(conceptId);

        if (existing?.childrenLoaded) {
            return existing.narrower;
        }

        if (inflightChildFetches.has(conceptId)) {
            return inflightChildFetches.get(conceptId)!;
        }

        const fetchPromise = (async () => {
            const fetchedChildren = (await fetchConceptChildren(
                conceptId,
            )) as Concept[];

            // For each fetched child, reuse the canonical Concept object
            // already in the map if one exists. A polyhierarchical concept
            // (one with multiple parents) appears in the API response for
            // every parent that is expanded. Without this, each parent load
            // creates a separate JS object for the same concept:
            //   parentA.narrower = [C_a]
            //   parentE.narrower = [C_e]   (different objects, same id)
            // When loadChildren("C") later fires, it updates only the object
            // in conceptsById (whichever was stored last), leaving the other
            // stale copy permanently un-expandable. Reusing the canonical
            // object ensures all parents share the same reference, so a
            // single update propagates to every occurrence in the tree.
            const children = fetchedChildren.map((child) => {
                const canonicalChild = conceptsById.value.get(child.id);
                if (canonicalChild) {
                    return canonicalChild;
                }
                child.narrower = child.narrower ?? [];
                conceptsById.value.set(child.id, child);
                return child;
            });

            const concept = conceptsById.value.get(conceptId);
            if (concept) {
                concept.narrower = children;
                concept.childrenLoaded = true;
            }
            inflightChildFetches.delete(conceptId);
            return children;
        })();

        inflightChildFetches.set(conceptId, fetchPromise);
        return fetchPromise;
    }

    function findConcept(conceptId: string): Concept | null {
        return conceptsById.value.get(conceptId) ?? null;
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
        loadChildren,
        getNarrower,
        findConcept,
        getParentPaths,
    };
});
