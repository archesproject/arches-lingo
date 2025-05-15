<script setup lang="ts">
import { computed, inject, nextTick, onMounted, ref, watch } from "vue";

import { useRoute, useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Tree from "primevue/tree";

import TreeRow from "@/arches_lingo/components/tree/components/TreeRow/TreeRow.vue";
import PresentationControls from "@/arches_controlled_lists/components/tree/PresentationControls.vue";

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
import { getItemLabel } from "@/arches_component_lab/utils.ts";

import type { ComponentPublicInstance, Ref } from "vue";
import type { RouteLocationNormalizedLoadedGeneric } from "vue-router";
import type {
    TreePassThroughMethodOptions,
    TreeExpandedKeys,
    TreeSelectionKeys,
} from "primevue/tree";
import type { TreeNode } from "primevue/treenode";
import type { Language } from "@/arches_component_lab/types";
import type { IconLabels, Scheme, Concept } from "@/arches_lingo/types";

const toast = useToast();
const { $gettext } = useGettext();
const route = useRoute();
const router = useRouter();

// Defining these in the parent avoids re-running $gettext in thousands of children.
const NEW = "new";
const FOCUS = $gettext("Focus");
const UNFOCUS = $gettext("Unfocus");
const ADD_CHILD = $gettext("Add child");

const iconLabels: IconLabels = Object.freeze({
    concept: $gettext("Concept"),
    scheme: $gettext("Scheme"),
});

const schemes: Ref<Scheme[]> = ref([]);
const focusedNode: Ref<TreeNode | null> = ref(null);
const selectedKeys: Ref<TreeSelectionKeys> = ref({});
const expandedKeys: Ref<TreeExpandedKeys> = ref({});
const filterValue = ref("");
const treeDOMRef: Ref<ComponentPublicInstance | null> = ref(null);
const selectedLanguage = inject(selectedLanguageKey) as Ref<Language>;
const systemLanguage = inject(systemLanguageKey) as Language;
const nextFilterChangeNeedsExpandAll = ref(false);
const expandedKeysSnapshotBeforeSearch = ref<TreeExpandedKeys>({});
const rerenderTree = ref(0);
const newTreeItemParentPath = ref<Concept[] | Scheme[]>([]);

const tree = computed(() => {
    return treeFromSchemes(
        schemes.value,
        selectedLanguage.value,
        systemLanguage,
        iconLabels,
        focusedNode.value,
    );
});

// React to route changes.
watch(route, (newRoute) => {
    selectNodeFromRoute(newRoute);
});

onMounted(async () => {
    try {
        const priorSortedSchemeIds = tree.value.map((node) => node.key);
        const concepts = await fetchConcepts();

        schemes.value = (concepts.schemes as Scheme[]).sort((a, b) => {
            return (
                priorSortedSchemeIds.indexOf(a.id) -
                priorSortedSchemeIds.indexOf(b.id)
            );
        });

        selectNodeFromRoute(route);
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch concepts"),
            detail: (error as Error).message,
        });
    }
});

function expandAll() {
    for (const node of tree.value) {
        expandNode(node);
    }
    expandedKeys.value = { ...expandedKeys.value };
}

function collapseAll() {
    expandedKeys.value = {};
}

function expandNode(node: TreeNode) {
    if (node.children && node.children.length) {
        expandedKeys.value[node.key] = true;
        for (const child of node.children) {
            expandNode(child);
        }
    }
}

function expandPathsToFilterResults(newFilterValue: string) {
    // https://github.com/primefaces/primevue/issues/3996
    if (filterValue.value && !newFilterValue) {
        expandedKeys.value = { ...expandedKeysSnapshotBeforeSearch.value };
        expandedKeysSnapshotBeforeSearch.value = {};
        // Rerender to avoid error emitted in PrimeVue tree re: aria-selected.
        rerenderTree.value += 1;
    }
    // Expand all on the first interaction with the filter, or if the user
    // has collapsed a node and changes the filter.
    if (
        (!filterValue.value && newFilterValue) ||
        (nextFilterChangeNeedsExpandAll.value &&
            filterValue.value !== newFilterValue)
    ) {
        expandedKeysSnapshotBeforeSearch.value = { ...expandedKeys.value };
        expandAll();
    }
    nextFilterChangeNeedsExpandAll.value = false;
}

function getInputElement() {
    if (treeDOMRef.value !== null) {
        return treeDOMRef.value.$el.ownerDocument.querySelector(
            'input[data-pc-name="pcfilterinput"]',
        ) as HTMLInputElement;
    }
}

function restoreFocusToInput() {
    // The current implementation of collapsing all nodes when
    // backspacing out the search value relies on rerendering the
    // <Tree> component. Restore focus to the input element.
    if (rerenderTree.value > 0) {
        const inputEl = getInputElement();
        if (inputEl) {
            inputEl.focus();
        }
    }
}

function snoopOnFilterValue() {
    // If we wait to react to the emitted filter event, the templated rows
    // will have already rendered. (<TreeRow> bolds search terms.)
    const inputEl = getInputElement();
    if (inputEl) {
        expandPathsToFilterResults(inputEl.value);
        filterValue.value = inputEl.value;
    }
}

function lazyLabelLookup(node: TreeNode) {
    return getItemLabel(
        node.data,
        selectedLanguage.value.code,
        systemLanguage.code,
    ).value;
}

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
    <PresentationControls
        :expand-all
        :collapse-all
    />
    <Tree
        v-if="tree"
        ref="treeDOMRef"
        :key="rerenderTree"
        v-model:selection-keys="selectedKeys"
        v-model:expanded-keys="expandedKeys"
        :value="tree"
        :filter="true"
        :filter-by="lazyLabelLookup"
        filter-mode="lenient"
        :filter-placeholder="$gettext('Find')"
        selection-mode="single"
        style="display: flex; flex-direction: column; overflow-y: hidden"
        :pt="{
            pcFilter: {
                root: {
                    ariaLabel: $gettext('Find'),
                    style: {
                        width: '100%',
                        marginBottom: '1rem',
                        display: 'flex',
                    },
                },
            },
            nodeContent: ({ instance }: TreePassThroughMethodOptions) => {
                return {
                    style: instance.node.data.id === NEW && {
                        backgroundColor: 'rgb(250 247 207)',
                    },
                };
            },
            nodeIcon: ({ instance }: TreePassThroughMethodOptions) => {
                return { ariaLabel: instance.node.iconLabel };
            },
            nodeLabel: {
                style: { textWrap: 'nowrap' },
            },
            hooks: {
                onBeforeUpdate: snoopOnFilterValue,
                onMounted: restoreFocusToInput,
            },
        }"
        @node-collapse="nextFilterChangeNeedsExpandAll = true"
        @node-select="onNodeSelect"
    >
        <template #default="slotProps">
            <TreeRow
                :id="slotProps.node.data.id"
                :focused-node="focusedNode"
                :filter-value="filterValue"
                :node="slotProps.node"
                :focus-label="FOCUS"
                :unfocus-label="UNFOCUS"
                :add-child-label="ADD_CHILD"
            />
        </template>
    </Tree>
</template>
<style scoped>
:deep(.p-tree-filter-input) {
    border-radius: 2px;
}
</style>