import { getItemLabel } from "@/arches_vue_utils/utils.ts";

import type { TreeNode } from "primevue/treenode";
import type { Language } from "@/arches_vue_utils/types";
import type {
    Concept,
    IconLabels,
    NodeAndParentInstruction,
    Scheme,
} from "@/arches_lingo/types";

// Duck-typing helpers
export function dataIsScheme(data: Concept | Scheme) {
    return (data as Scheme).top_concepts !== undefined;
}
export function dataIsConcept(data: Concept | Scheme) {
    return !dataIsScheme(data);
}

// Tree builder
export function treeFromSchemes(
    schemes: Scheme[],
    selectedLanguage: Language,
    systemLanguage: Language,
    iconLabels: IconLabels,
    focusedNode: TreeNode | null,
): TreeNode[] {
    function buildNode(
        item: Concept | Scheme,
        childNodes: TreeNode[],
    ): TreeNode {
        return {
            key: item.id,
            label: getItemLabel(
                item,
                selectedLanguage.code,
                systemLanguage.code,
            ).value,
            children: childNodes,
            data: item,
            icon: dataIsScheme(item) ? "pi pi-folder" : "pi pi-tag",
            iconLabel: dataIsScheme(item)
                ? iconLabels.scheme
                : iconLabels.concept,
        };
    }

    // When traversing the tree, notice whether the node is focused, and if so,
    // memoize/instruct that the parent should hide its siblings.
    function processItem(
        item: Concept | Scheme,
        children: Concept[],
    ): NodeAndParentInstruction {
        let childrenAsNodes: TreeNode[];
        const nodesAndInstructions = children.map((child) =>
            processItem(child, child.narrower),
        );
        const parentOfFocusedNode = nodesAndInstructions.find(
            (obj) => obj.shouldHideSiblings,
        );
        if (parentOfFocusedNode) {
            childrenAsNodes = [parentOfFocusedNode.node];
        } else {
            childrenAsNodes = nodesAndInstructions.map((obj) => obj.node);
        }

        const node: TreeNode = buildNode(item, childrenAsNodes);
        let shouldHideSiblings = !!parentOfFocusedNode;
        if (!shouldHideSiblings) {
            const focalNode = node.children!.find(
                (child: TreeNode) => child.data.id === focusedNode?.data?.id,
            );
            if (focalNode) {
                node.children = [focalNode];
                shouldHideSiblings = true;
            }
        }
        return { node, shouldHideSiblings };
    }

    // If this scheme is focused, immediately process and return it.
    const focalScheme = schemes.find((sch) => sch.id === focusedNode?.data?.id);
    if (focalScheme) {
        return [processItem(focalScheme, focalScheme.top_concepts).node];
    }

    // Otherwise, process schemes until a focused node is found.
    const reshapedSchemes = [];
    for (const scheme of schemes) {
        const { node, shouldHideSiblings } = processItem(
            scheme,
            scheme.top_concepts,
        );
        if (shouldHideSiblings) {
            return [node];
        } else {
            reshapedSchemes.push(node);
        }
    }

    return reshapedSchemes;
}

export function checkDeepEquality(value1: unknown, value2: unknown): boolean {
    if (typeof value1 !== typeof value2) {
        return false;
    }

    if (
        typeof value1 !== "object" ||
        value1 === null ||
        typeof value2 !== "object" ||
        value2 === null
    ) {
        return value1 === value2;
    }

    if (Array.isArray(value1) && Array.isArray(value2)) {
        return (
            value1.length === value2.length &&
            value1.every((item, index) =>
                checkDeepEquality(item, value2[index]),
            )
        );
    }

    const object1 = value1 as Record<string, unknown>;
    const object2 = value2 as Record<string, unknown>;

    return Object.keys(object1).every((key) => {
        return checkDeepEquality(object1[key], object2[key]);
    });
}
