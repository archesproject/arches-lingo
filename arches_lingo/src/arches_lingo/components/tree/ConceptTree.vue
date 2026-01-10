<script setup lang="ts">
import {
    computed,
    inject,
    nextTick,
    onMounted,
    onUnmounted,
    ref,
    watch,
} from "vue";

import { useRoute, useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";
import Skeleton from "primevue/skeleton";
import InputText from "primevue/inputtext";
import Message from "primevue/message";

import Tree from "primevue/tree";

import TreeRow from "@/arches_lingo/components/tree/components/TreeRow/TreeRow.vue";

import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
} from "@/arches_controlled_lists/constants.ts";
import {
    selectedLanguageKey,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";

import { findNodeInTree } from "@/arches_controlled_lists/utils.ts";
import { fetchConcepts } from "@/arches_lingo/api.ts";

import {
    treeFromSchemes,
    navigateToSchemeOrConcept,
} from "@/arches_lingo/utils.ts";

import { useCappedTreeFilter } from "@/arches_lingo/components/tree/utils/capped-filter.ts";

import type { Ref } from "vue";
import type { RouteLocationNormalizedLoadedGeneric } from "vue-router";
import type {
    TreePassThroughMethodOptions,
    TreeExpandedKeys,
    TreeSelectionKeys,
} from "primevue/tree";
import type { TreeNode } from "primevue/treenode";
import type { Language } from "@/arches_component_lab/types";
import type { IconLabels, Scheme, Concept } from "@/arches_lingo/types";

const props = withDefaults(
    defineProps<{
        concepts?: {
            schemes: Scheme[];
        };
    }>(),
    {
        concepts: undefined,
    },
);

const toast = useToast();
const { $gettext } = useGettext();
const route = useRoute();
const router = useRouter();

const NEW = "new";
const FOCUS = $gettext("Focus");
const UNFOCUS = $gettext("Unfocus");
const ADD_CHILD = $gettext("Add child");
const DELETE = $gettext("Delete");
const EXPORT = $gettext("Export");

const FILTER_CONCEPTS = $gettext("Filter concepts");
const FILTER_CAPPED_MESSAGE = $gettext("Please refine your query.");

const iconLabels: IconLabels = Object.freeze({
    concept: $gettext("Concept"),
    scheme: $gettext("Scheme"),
});

const schemes: Ref<Scheme[]> = ref([]);
const focusedNode: Ref<TreeNode | null> = ref(null);
const selectedKeys: Ref<TreeSelectionKeys> = ref({});
const expandedKeys: Ref<TreeExpandedKeys> = ref({});
const filterValue = ref("");
const selectedLanguage = inject(selectedLanguageKey) as Ref<Language>;
const systemLanguage = inject(systemLanguageKey) as Language;
const newTreeItemParentPath = ref<Concept[] | Scheme[]>([]);

const treeContainer = ref<HTMLElement | null>(null);
let conceptTreeVisibilityObserver: IntersectionObserver | null = null;
let wasTreeVisible = false;

const FILTER_RENDER_CAP = 2500;
const FILTER_DEBOUNCE_MS = 500;
const SKELETON_ROW_COUNT = 14;

const tree = computed(() => {
    return treeFromSchemes(
        schemes.value,
        selectedLanguage.value,
        systemLanguage,
        iconLabels,
        focusedNode.value,
    );
});

function getSearchableText(treeNode: TreeNode) {
    const nodeData = treeNode.data as unknown as Scheme | Concept;

    if ("top_concepts" in nodeData) {
        return "";
    }

    const nodeLabelText = (treeNode.label ?? "").toString();
    const labelValuesFromData = (nodeData.labels ?? [])
        .map((labelItem) => (labelItem?.value ?? "").toString())
        .join(" ");

    return `${nodeLabelText} ${labelValuesFromData}`.toLowerCase();
}

const { debouncedFilterValue, filteredTree, isFilterCapped } =
    useCappedTreeFilter(
        tree,
        expandedKeys,
        filterValue,
        FILTER_DEBOUNCE_MS,
        FILTER_RENDER_CAP,
        getSearchableText,
    );

watch(route, (newRoute) => {
    selectNodeFromRoute(newRoute);
});

onMounted(async () => {
    let concepts = props.concepts;

    if (!props.concepts) {
        try {
            concepts = await fetchConcepts();
        } catch (error) {
            toast.add({
                severity: ERROR,
                life: DEFAULT_ERROR_TOAST_LIFE,
                summary: $gettext("Unable to fetch concepts"),
                detail: (error as Error).message,
            });
        }
    }

    const priorSortedSchemeIds = tree.value.map((treeNode) => treeNode.key);

    schemes.value = (concepts!.schemes as Scheme[]).sort((schemeA, schemeB) => {
        return (
            priorSortedSchemeIds.indexOf(schemeA.id) -
            priorSortedSchemeIds.indexOf(schemeB.id)
        );
    });

    await nextTick();

    selectNodeFromRoute(route);

    conceptTreeVisibilityObserver = new IntersectionObserver(
        (intersectionEntries) => {
            const hasVisibleEntry = intersectionEntries.some(
                (intersectionEntry) => intersectionEntry.isIntersecting,
            );

            if (hasVisibleEntry && !wasTreeVisible) {
                wasTreeVisible = true;
                scrollToItemInTree(route.params.id as string);
                return;
            }

            if (!hasVisibleEntry) {
                wasTreeVisible = false;
            }
        },
        { threshold: 0.01 },
    );

    if (treeContainer.value) {
        conceptTreeVisibilityObserver.observe(treeContainer.value);
    }
});

onUnmounted(() => {
    if (conceptTreeVisibilityObserver) {
        conceptTreeVisibilityObserver.disconnect();
        conceptTreeVisibilityObserver = null;
    }
});

function updateSelectedAndExpanded(node: TreeNode) {
    expandedKeys.value = {
        ...expandedKeys.value,
        [node.key]: true,
    };
}

function findNodeById(concepts: Concept | Concept[], targetId: string) {
    const queue = [];

    if (Array.isArray(concepts)) {
        for (const node of concepts) {
            queue.push({ node, path: [node] });
        }
    } else {
        queue.push({ node: concepts, path: [concepts] });
    }

    while (queue.length > 0) {
        const queueItem = queue.shift() as
            | { node: Concept; path: Concept[] }
            | undefined;

        if (!queueItem) {
            continue;
        }

        const { node: currentNode, path: path } = queueItem;

        if (currentNode.id === targetId) {
            return { node: currentNode, path: path };
        }

        if (currentNode.narrower && Array.isArray(currentNode.narrower)) {
            for (const childNode of currentNode.narrower) {
                queue.push({ node: childNode, path: [...path, childNode] });
            }
        }
    }

    return null;
}

function resetNewTreeItemParentPath() {
    if (newTreeItemParentPath.value.length) {
        const parent = newTreeItemParentPath.value.at(-1);

        if ("top_concepts" in parent!) {
            parent.top_concepts.shift();
        } else if ("narrower" in parent!) {
            parent.narrower.shift();
        }

        newTreeItemParentPath.value = [];
    }
}

function scrollToItemInTree(nodeId: string) {
    try {
        const { found, path } = findNodeInTree(tree.value, nodeId);

        if (found) {
            const itemsToExpandIds = path.map(
                (itemInPath: TreeNode) => itemInPath.key,
            );

            expandedKeys.value = {
                ...expandedKeys.value,
                ...Object.fromEntries(
                    itemsToExpandIds.map((item: string) => [item, true]),
                ),
                [found.key]: true,
            };
            selectedKeys.value = { [found.data.id]: true };

            nextTick(() => {
                const element = document.getElementById(found.data.id);

                if (element) {
                    element.scrollIntoView({
                        behavior: "smooth",
                        block: "center",
                    });
                }
            });
        }
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (error) {
        return null;
    }
}

function addNewConceptToTree(schemeId: string, parentId: string) {
    const targetScheme = schemes.value.find(
        (schemeItem) => schemeItem.id === schemeId,
    );
    if (!targetScheme) return;

    const newConcept = {
        id: NEW,
        labels: [
            {
                language_id: selectedLanguage.value.code,
                value: $gettext("New concept"),
                valuetype_id: "preferred label",
            },
        ],
        narrower: [],
    };

    let parentPath = [targetScheme];

    if (schemeId === parentId) {
        // adding top concept to scheme
        targetScheme.top_concepts.unshift(newConcept);
    } else {
        // adding narrower concept to existing concept
        const searchResult = findNodeById(targetScheme.top_concepts, parentId);
        if (!searchResult) return;

        searchResult.node.narrower.unshift(newConcept);
        parentPath = [
            targetScheme,
            ...(searchResult.path as unknown as Scheme[]),
        ];
    }

    newTreeItemParentPath.value = parentPath;

    schemes.value = schemes.value.map((existingScheme) => {
        return existingScheme.id === schemeId ? targetScheme : existingScheme;
    });
}

function selectNodeFromRoute(newRoute: RouteLocationNormalizedLoadedGeneric) {
    resetNewTreeItemParentPath();

    if (newRoute.params.id === NEW) {
        addNewConceptToTree(
            newRoute.query.scheme as string,
            newRoute.query.parent as string,
        );
    }

    scrollToItemInTree(newRoute.params.id as string);
}

function onNodeSelect(node: TreeNode) {
    if (node.data.id === NEW) {
        return;
    }

    updateSelectedAndExpanded(node);
    navigateToSchemeOrConcept!(router, node.data);
}
</script>

<template>
    <div
        ref="treeContainer"
        class="concept-tree-layout"
    >
        <div class="filter-container">
            <InputText
                v-model="filterValue"
                class="tree-filter-input"
                type="text"
                :placeholder="FILTER_CONCEPTS"
                :aria-label="FILTER_CONCEPTS"
            />
            <Message
                v-if="isFilterCapped"
                severity="warn"
                :closable="false"
                class="filter-cap-message"
            >
                {{ FILTER_CAPPED_MESSAGE }}
            </Message>
        </div>

        <div
            v-if="!tree.length"
            class="skeleton-container"
        >
            <Skeleton
                v-for="number in SKELETON_ROW_COUNT"
                :key="number"
                class="skeleton-row"
            />
        </div>

        <Tree
            v-else
            v-model:selection-keys="selectedKeys"
            v-model:expanded-keys="expandedKeys"
            :value="filteredTree"
            class="concept-tree"
            selection-mode="single"
            :pt="{
                nodeContent: ({ instance }: TreePassThroughMethodOptions) => {
                    return {
                        class:
                            instance.node.data.id === NEW
                                ? 'new-node'
                                : undefined,
                    };
                },
                nodeIcon: ({ instance }: TreePassThroughMethodOptions) => {
                    return { ariaLabel: instance.node.iconLabel };
                },
                nodeLabel: {
                    style: { textWrap: 'nowrap' },
                },
            }"
            @node-select="onNodeSelect"
        >
            <template #default="slotProps">
                <TreeRow
                    :id="slotProps.node.data.id"
                    v-model:focused-node="focusedNode"
                    :filter-value="debouncedFilterValue"
                    :node="slotProps.node"
                    :focus-label="FOCUS"
                    :unfocus-label="UNFOCUS"
                    :add-child-label="ADD_CHILD"
                    :delete-label="DELETE"
                    :export-label="EXPORT"
                />
            </template>
        </Tree>
    </div>
</template>

<style scoped>
.concept-tree-layout {
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.filter-container {
    padding-top: 1rem;
    padding-inline: 0.5rem;
    padding-bottom: 1rem;
    border-bottom: 0.0625rem solid var(--p-menubar-border-color);
}

.tree-filter-input {
    border-radius: 0.125rem;
    width: 100%;
}

.filter-cap-message {
    margin-top: 1rem;
}

.concept-tree {
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow-y: hidden;
    padding: 0;
    font-size: var(--p-lingo-font-size-smallnormal);
}

:deep(.p-tree-root) {
    height: 100%;
}

.skeleton-container {
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
    padding: var(--p-tree-padding);
    width: 100%;
    gap: 1rem;
    padding-top: 1rem;
}

.skeleton-container :deep(.p-skeleton.skeleton-row) {
    flex: 1 1 0;
    min-height: 1.75rem;
    height: 100%;
}

:deep(.new-node),
:deep(.new-node *) {
    background-color: var(--p-yellow-500) !important;
    color: var(--p-tree-node-color) !important;
}
</style>
