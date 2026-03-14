import { routeNames } from "@/arches_lingo/routes.ts";

import { createLingoResource, upsertLingoTile } from "@/arches_lingo/api.ts";
import {
    NEW_CONCEPT,
    CONCEPT_ICON,
    GUIDE_TERM_ICON,
    SCHEME_ICON,
    TOP_CONCEPT_ICON,
    CONCEPT_TYPE_NODE_ALIAS,
} from "@/arches_lingo/constants.ts";
import { fetchTileData } from "@/arches_component_lab/generics/GenericCard/api.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";

import type { TreeNode } from "primevue/treenode";
import type { Language } from "@/arches_component_lab/types.ts";
import type {
    Concept,
    ConceptType,
    IconLabels,
    NodeAndParentInstruction,
    ResourceInstanceResult,
    ResourceDescriptor,
    Scheme,
    SchemeStatement,
    SearchResultItem,
} from "@/arches_lingo/types";
import type { Router } from "vue-router/dist/vue-router";
import type { ConceptInstance } from "@/arches_lingo/types.ts";

export function dataIsScheme(data: Concept | Scheme) {
    return (data as Scheme).top_concepts !== undefined;
}
export function dataIsConcept(data: Concept | Scheme) {
    return !dataIsScheme(data);
}

export function getConceptIcon(
    item:
        | Concept
        | SearchResultItem
        | { guide_term?: boolean; top_concept?: boolean },
): string {
    if (item.guide_term) return GUIDE_TERM_ICON;
    if ((item as { top_concept?: boolean }).top_concept)
        return TOP_CONCEPT_ICON;
    return CONCEPT_ICON;
}

export function getItemIcon(item: Concept | Scheme): string {
    if (dataIsScheme(item)) {
        return SCHEME_ICON;
    }
    return getConceptIcon(item as Concept);
}

export function navigateToSchemeOrConcept(
    router: Router,
    value: Concept | Scheme | typeof NEW_CONCEPT,
    queryParams: { [key: string]: string } = {},
) {
    // TODO: Consider adding some sort of short-circuiting of fetchUser
    if (value === NEW_CONCEPT) {
        return router.push({
            name: routeNames.concept,
            params: { id: "new" },
            query: queryParams,
        });
    } else if (dataIsScheme(value)) {
        return router.push({
            name: routeNames.scheme,
            params: { id: value.id },
            query: queryParams,
        });
    } else if (dataIsConcept(value)) {
        return router.push({
            name: routeNames.concept,
            params: { id: value.id },
            query: queryParams,
        });
    }
}

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
            icon: getItemIcon(item),
            iconLabel: getIconLabel(item, iconLabels),
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

export function getAutonym(code: string, fallback: string): string {
    try {
        const name = new Intl.DisplayNames([code], { type: "language" }).of(
            code,
        );
        if (name) {
            return name;
        }
    } catch {
        // Intl.DisplayNames may not support every code — fall through.
    }
    return fallback;
}

export function getStatementText(
    statements: SchemeStatement[],
    preferredLanguageCode: string,
    systemLanguageCode: string,
): string {
    if (!statements.length) return "";

    function rankLanguage(lang?: string): number {
        if (lang === preferredLanguageCode) return 2;
        if (lang === systemLanguageCode) return 1;
        return 0;
    }

    const best = statements.reduce((bestMatch, current) => {
        const currentLang =
            current.aliased_data?.statement_language?.display_value?.toLowerCase();
        const bestLang =
            bestMatch.aliased_data?.statement_language?.display_value?.toLowerCase();
        return rankLanguage(currentLang) > rankLanguage(bestLang)
            ? current
            : bestMatch;
    });

    return best.aliased_data?.statement_content?.display_value ?? "";
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
        const blankConceptTypeTile = (await fetchTileData(
            graphSlug,
            CONCEPT_TYPE_NODE_ALIAS,
        )) as unknown as ConceptType;

        const isTop = scheme === parent;

        const aliased_data = {
            [nodegroupAlias]: [{ aliased_data: formData }],
            part_of_scheme: {
                aliased_data: { part_of_scheme: scheme },
            },
            type: { aliased_data: blankConceptTypeTile.aliased_data },
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

export function getIconLabel(
    item: Concept | Scheme,
    iconLabels: IconLabels,
): string {
    if (dataIsScheme(item)) {
        return iconLabels.scheme;
    }

    if ((item as Concept).guide_term) {
        return iconLabels.guideTerm;
    }

    if ((item as Concept).top_concept) {
        return iconLabels.topConcept;
    }

    return iconLabels.concept;
}

// Advanced Search helpers

let nextConditionId = Date.now();

/**
 * Generate a unique ID for search conditions and groups.
 * Shared between AdvancedSearch page and FacetGroup component.
 */
export function generateConditionId(): string {
    return `cond-${nextConditionId++}`;
}
