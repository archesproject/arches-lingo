import { ref, nextTick } from "vue";
import { beforeEach, afterEach, vi } from "vitest";
import { useCappedTreeFilter } from "@/arches_lingo/components/tree/utils/capped-filter.ts";

import type { TreeNode } from "primevue/treenode";
import type { TreeExpandedKeys } from "primevue/tree";

function buildNode(
    key: string,
    label: string,
    children: TreeNode[] = [],
): TreeNode {
    return { key, label, data: { label }, children };
}

const FILTER_DEBOUNCE_MS = 50;
const DEFAULT_CAP = 50;

function mountFilter(treeNodes: TreeNode[], cap = DEFAULT_CAP) {
    const treeRef = ref<TreeNode[]>(treeNodes);
    const expandedKeys = ref<TreeExpandedKeys>({});
    const filterValue = ref("");

    const result = useCappedTreeFilter(
        treeRef,
        expandedKeys,
        filterValue,
        FILTER_DEBOUNCE_MS,
        cap,
        (node: TreeNode) => ((node.label as string) ?? "").toLowerCase(),
    );

    return { treeRef, expandedKeys, filterValue, ...result };
}

async function applyFilter(filterValue: { value: string }, searchText: string) {
    filterValue.value = searchText;
    await nextTick();
    vi.runAllTimers();
    await nextTick();
}

describe("useCappedTreeFilter", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("Should return the full tree when no filter is applied", () => {
        const tree = [buildNode("1", "Apple"), buildNode("2", "Banana")];
        const { filteredTree } = mountFilter(tree);
        expect(filteredTree.value.length).toEqual(2);
    });

    it("Should filter nodes to only those matching the search value", async () => {
        const tree = [
            buildNode("1", "Apple"),
            buildNode("2", "Banana"),
            buildNode("3", "Apricot"),
        ];
        const { filteredTree, filterValue } = mountFilter(tree);

        await applyFilter(filterValue, "ap");

        const filteredLabels = filteredTree.value.map((node) => node.label);
        expect(filteredLabels).toContain("Apple");
        expect(filteredLabels).toContain("Apricot");
        expect(filteredLabels).not.toContain("Banana");
    });

    it("Should include a parent node when only a child matches", async () => {
        const childNode = buildNode("1-1", "Seedless Grape");
        const parentNode = buildNode("1", "Fruits", [childNode]);
        const { filteredTree, filterValue } = mountFilter([parentNode]);

        await applyFilter(filterValue, "grape");

        expect(filteredTree.value.length).toEqual(1);
        expect(filteredTree.value[0].label).toEqual("Fruits");
        expect(filteredTree.value[0].children!.length).toEqual(1);
        expect(filteredTree.value[0].children![0].label).toEqual(
            "Seedless Grape",
        );
    });

    it("Should restore the full tree when the filter is cleared after being set", async () => {
        const tree = [buildNode("1", "Apple"), buildNode("2", "Banana")];
        const { filteredTree, filterValue } = mountFilter(tree);

        await applyFilter(filterValue, "apple");
        expect(filteredTree.value.length).toEqual(1);

        // Clearing the filter sets debouncedFilterValue immediately (no timeout)
        filterValue.value = "";
        await nextTick();
        await nextTick();
        expect(filteredTree.value.length).toEqual(2);
    });

    it("Should set isFilterCapped and revert to full tree when results exceed the cap", async () => {
        const smallCap = 2;
        const tree = [
            buildNode("1", "matching alpha"),
            buildNode("2", "matching beta"),
            buildNode("3", "matching gamma"),
        ];
        const { filteredTree, filterValue, isFilterCapped } = mountFilter(
            tree,
            smallCap,
        );

        await applyFilter(filterValue, "matching");

        expect(isFilterCapped.value).toBe(true);
        // When capped, the full unfiltered tree is shown
        expect(filteredTree.value.length).toEqual(3);
    });

    it("Should set isFilterCapped to false when results do not exceed the cap", async () => {
        const tree = [buildNode("1", "Apple"), buildNode("2", "Banana")];
        const { filterValue, isFilterCapped } = mountFilter(tree, DEFAULT_CAP);

        await applyFilter(filterValue, "apple");

        expect(isFilterCapped.value).toBe(false);
    });

    it("Should expand matched parent nodes when a filter is active", async () => {
        const childNode = buildNode("1-1", "Mandarin");
        const parentNode = buildNode("1", "Citrus Fruits", [childNode]);
        const { filterValue, expandedKeys } = mountFilter([parentNode]);

        await applyFilter(filterValue, "mandarin");

        expect(expandedKeys.value["1"]).toBe(true);
    });

    it("Should restore saved expanded keys when filter is cleared", async () => {
        const childNode = buildNode("1-1", "Child");
        const parentNode = buildNode("1", "Parent", [childNode]);
        const { filterValue, expandedKeys } = mountFilter([parentNode]);

        // Expand a node before filtering
        expandedKeys.value = { "1": true };

        await applyFilter(filterValue, "child");

        filterValue.value = "";
        await nextTick();
        await nextTick();

        expect(expandedKeys.value["1"]).toBe(true);
    });

    it("Should not include nodes that do not match and have no matching descendants", async () => {
        const tree = [buildNode("1", "Apple"), buildNode("2", "Banana")];
        const { filteredTree, filterValue } = mountFilter(tree);

        await applyFilter(filterValue, "cherry");

        expect(filteredTree.value.length).toEqual(0);
    });
});
