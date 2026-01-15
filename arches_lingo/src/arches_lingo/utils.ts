import { routeNames } from "@/arches_lingo/routes.ts";

import { createLingoResource, upsertLingoTile } from "@/arches_lingo/api.ts";
import { NEW_CONCEPT } from "@/arches_lingo/constants.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";

import type { TreeNode } from "primevue/treenode";
import type { Language } from "@/arches_component_lab/types.ts";
import type {
    Concept,
    IconLabels,
    NodeAndParentInstruction,
    ResourceInstanceResult,
    ResourceDescriptor,
    Scheme,
    SearchResultItem,
} from "@/arches_lingo/types";
import type { Router } from "vue-router/dist/vue-router";
import type { ConceptInstance } from "@/arches_lingo/types.ts";

// Duck-typing helpers
export function dataIsScheme(data: Concept | Scheme) {
    return (data as Scheme).top_concepts !== undefined;
}
export function dataIsConcept(data: Concept | Scheme) {
    return !dataIsScheme(data);
}

export function navigateToSchemeOrConcept(
    router: Router,
    value: Concept | Scheme | typeof NEW_CONCEPT,
    queryParams: { [key: string]: string } = {},
) {
    // TODO: Consider adding some sort of short-circuiting of fetchUser
    if (value === NEW_CONCEPT) {
        router.push({
            name: routeNames.concept,
            params: { id: "new" },
            query: queryParams,
        });
    } else if (dataIsScheme(value)) {
        router.push({
            name: routeNames.scheme,
            params: { id: value.id },
            query: queryParams,
        });
    } else if (dataIsConcept(value)) {
        router.push({
            name: routeNames.concept,
            params: { id: value.id },
            query: queryParams,
        });
    }
}

// Tree builder
export function treeFromSchemes(
    schemes: Scheme[],
    selectedLanguage: Language,
    systemLanguage: Language,
    iconLabels: IconLabels,
    focusedOccurrenceKey: string | null,
): TreeNode[] {
    function buildOccurrenceKey(schemeId: string, pathIds: string[]) {
        return `${schemeId}::${pathIds.join(">")}`;
    }

    function buildNode(
        item: Concept | Scheme,
        childNodes: TreeNode[],
        schemeId: string,
        pathIds: string[],
    ): TreeNode {
        const key =
            "top_concepts" in item
                ? item.id
                : buildOccurrenceKey(schemeId, pathIds);

        return {
            key,
            label: getItemLabel(
                item,
                selectedLanguage.code,
                systemLanguage.code,
            ).value,
            children: childNodes,
            data: {
                ...item,
                schemeId,
            },
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
        schemeId: string,
        pathIds: string[],
    ): NodeAndParentInstruction {
        const nodesAndInstructions = children.map((child) =>
            processItem(child, child.narrower, schemeId, [
                ...pathIds,
                child.id,
            ]),
        );

        const parentOfFocusedNode = nodesAndInstructions.find(
            (obj) => obj.shouldHideSiblings,
        );

        const childrenAsNodes = parentOfFocusedNode
            ? [parentOfFocusedNode.node]
            : nodesAndInstructions.map((obj) => obj.node);

        const node: TreeNode = buildNode(
            item,
            childrenAsNodes,
            schemeId,
            pathIds,
        );

        let shouldHideSiblings = !!parentOfFocusedNode;

        if (!shouldHideSiblings && focusedOccurrenceKey) {
            const focalChild = (node.children ?? []).find(
                (childNode: TreeNode) => childNode.key === focusedOccurrenceKey,
            );
            if (focalChild) {
                node.children = [focalChild];
                shouldHideSiblings = true;
            }
        }

        return { node, shouldHideSiblings };
    }

    // If this scheme is focused, immediately process and return it.
    const focalScheme = schemes.find(
        (schemeItem) => schemeItem.id === focusedOccurrenceKey,
    );
    if (focalScheme) {
        return [
            processItem(
                focalScheme,
                focalScheme.top_concepts,
                focalScheme.id,
                [],
            ).node,
        ];
    }

    // Otherwise, process schemes until a focused node is found.
    const reshapedSchemes = [];
    for (const scheme of schemes) {
        const { node, shouldHideSiblings } = processItem(
            scheme,
            scheme.top_concepts,
            scheme.id,
            [],
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

    if (Array.isArray(value1) && Array.isArray(value2)) {
        return (
            value1.length === value2.length &&
            value1.every((item, index) =>
                checkDeepEquality(item, value2[index]),
            )
        );
    }

    if (
        typeof value1 !== "object" ||
        value1 === null ||
        typeof value2 !== "object" ||
        value2 === null
    ) {
        return value1 === value2;
    }

    const object1 = value1 as Record<string, unknown>;
    const object2 = value2 as Record<string, unknown>;

    return Object.keys(object1).every((key) => {
        return checkDeepEquality(object1[key], object2[key]);
    });
}

export function getParentLabels(
    item: SearchResultItem,
    preferredLanguageCode: string,
    systemLanguageCode: string,
): string {
    const arrowIcon = " → ";

    if (!item.parents || item.parents.length === 0) {
        return "";
    }

    return item.parents[0].reduce((acc, parent, index) => {
        const label = getItemLabel(
            parent,
            preferredLanguageCode,
            systemLanguageCode,
        ).value;
        if (label) {
            return acc + (index > 0 ? arrowIcon : "") + label;
        }
        return acc;
    }, "");
}

export function extractDescriptors(
    resource: ResourceInstanceResult | undefined,
    selectedLanguage: Language,
): ResourceDescriptor {
    const descriptors = resource?.descriptors;
    const schemeDescriptor: ResourceDescriptor = {
        name: "",
        description: "",
        language: "",
    };
    if (descriptors) {
        const languagecode = descriptors[selectedLanguage.code]
            ? selectedLanguage.code
            : Object.keys(descriptors)[0];
        const descriptor =
            descriptors[selectedLanguage.code] ?? Object.values(descriptors)[0];
        if (descriptor) {
            schemeDescriptor.name = descriptor.name ?? "";
            schemeDescriptor.description = descriptor.description ?? "";
            schemeDescriptor.language = languagecode;
        }
    }
    return schemeDescriptor;
}

export async function createOrUpdateConcept(
    formData: Record<string, unknown>,
    graphSlug: string,
    nodegroupAlias: string,
    scheme: string,
    parent: string,
    router: Router,
    resourceInstanceId?: string,
    tileId?: string,
): Promise<string> {
    if (!resourceInstanceId) {
        const isTop = scheme === parent;

        const aliased_data = {
            [nodegroupAlias]: [{ aliased_data: formData }],
            part_of_scheme: {
                aliased_data: { part_of_scheme: scheme },
            },
        };

        if (isTop) {
            aliased_data.top_concept_of = [
                {
                    aliased_data: { top_concept_of: parent },
                },
            ];
        } else {
            aliased_data.classification_status = [
                {
                    aliased_data: {
                        classification_status_ascribed_classification: parent,
                    },
                },
            ];
        }

        const concept = await createLingoResource(
            { aliased_data } as ConceptInstance,
            graphSlug,
        );

        await router.push({
            name: graphSlug,
            params: { id: concept.resourceinstanceid },
        });

        return concept.aliased_data[nodegroupAlias][0].tileid;
    } else {
        const tile = await upsertLingoTile(graphSlug, nodegroupAlias, {
            resourceinstance: resourceInstanceId,
            aliased_data: { ...formData },
            tileid: tileId!,
        });

        return tile.tileid;
    }
}
