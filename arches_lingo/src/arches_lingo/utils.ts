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
    // Use a closure to avoid passing around params (selectedLanguage, etc).
    const conceptAsNodeAndInstruction = (
        concept: Concept,
    ): NodeAndParentInstruction => {
        return conceptOrSchemeAsNodeAndInstruction(concept, concept.narrower);
    };
    const schemeAsNodeAndInstruction = (
        scheme: Scheme,
    ): NodeAndParentInstruction => {
        return conceptOrSchemeAsNodeAndInstruction(scheme, scheme.top_concepts);
    };

    const conceptOrSchemeAsNodeAndInstruction = (
        labellable: Concept | Scheme,
        children: Concept[],
    ): NodeAndParentInstruction => {
        let childrenAsNodes: TreeNode[];
        const nodesAndInstructions = children.map((child) =>
            conceptAsNodeAndInstruction(child),
        );
        const parentOfFocusedNode = nodesAndInstructions.find(
            (obj) => obj.parentShouldHideSiblings,
        );
        if (parentOfFocusedNode) {
            childrenAsNodes = [parentOfFocusedNode.node];
        } else {
            childrenAsNodes = nodesAndInstructions.map((obj) => obj.node);
        }

        const node: TreeNode = {
            key: labellable.id,
            label: getItemLabel(
                labellable,
                selectedLanguage.code,
                systemLanguage.code,
            ).value,
            children: childrenAsNodes,
            data: labellable,
            iconLabel: dataIsScheme(labellable)
                ? iconLabels.scheme
                : iconLabels.concept,
        };
        let parentShouldHideSiblings = !!parentOfFocusedNode;
        if (!parentShouldHideSiblings) {
            const focalNodeIdx = node.children!.findIndex(
                (child: TreeNode) => child.data.id === focusedNode?.data?.id,
            );
            if (focalNodeIdx > -1) {
                node.children = [node.children![focalNodeIdx]];
                parentShouldHideSiblings = true;
            }
        }
        return { node, parentShouldHideSiblings };
    };

    const focalNodeIdx = schemes.findIndex(
        (scheme) => scheme.id === focusedNode?.data?.id,
    );
    if (focalNodeIdx > -1) {
        return [schemeAsNodeAndInstruction(schemes[focalNodeIdx]).node];
    }
    const nodesAndInstructions = schemes.map((scheme: Scheme) =>
        schemeAsNodeAndInstruction(scheme),
    );
    const parentOfFocusedNode = nodesAndInstructions.find(
        (obj) => obj.parentShouldHideSiblings,
    );
    if (parentOfFocusedNode) {
        return [parentOfFocusedNode.node];
    }
    return nodesAndInstructions.map((obj) => obj.node);
}
