<script setup lang="ts">
import { computed, inject, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import Tree from "primevue/tree";

import { getItemLabel } from "@/arches_vue_utils/utils.ts";
import PresentationControls from "@/arches_controlled_lists/components/tree/PresentationControls.vue";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
} from "@/arches_controlled_lists/constants.ts";
import { findNodeInTree } from "@/arches_controlled_lists/utils.ts";
import { fetchConcepts } from "@/arches_lingo/api.ts";
import {
    selectedLanguageKey,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";
import { treeFromSchemes, navigateToSchemeOrConcept } from "@/arches_lingo/utils.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import TreeRow from "@/arches_lingo/components/tree/components/TreeRow/TreeRow.vue";

import type { ComponentPublicInstance, Ref } from "vue";
import type { RouteLocationNormalizedLoadedGeneric } from "vue-router";
import type {
    TreePassThroughMethodOptions,
    TreeExpandedKeys,
    TreeSelectionKeys,
} from "primevue/tree";
import type { TreeNode } from "primevue/treenode";
import type { Language } from "@/arches_vue_utils/types";
import type {
    IconLabels,
    Scheme,
} from "@/arches_lingo/types";

const toast = useToast();
const { $gettext } = useGettext();
const route = useRoute();
const router = useRouter();

// Defining these in the parent avoids re-running $gettext in thousands of children.
const NEW = 'new';
const FOCUS = $gettext("Focus");
const UNFOCUS = $gettext("Unfocus");
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

const tree = computed(() =>{
    return treeFromSchemes(
        schemes.value,
        selectedLanguage.value,
        systemLanguage,
        iconLabels,
        focusedNode.value,
    )
});

// React to route changes.
watch(
    route, 
    (newRoute) => {
        selectNodeFromRoute(newRoute);
    },
);

onMounted(async() => {
    try {
        const priorSortedSchemeIds = tree.value.map((node) => node.key);
        const concepts = await fetchConcepts();

        schemes.value = (concepts.schemes as Scheme[]).sort(
            (a, b) => {
                return (
                    priorSortedSchemeIds.indexOf(a.id) - priorSortedSchemeIds.indexOf(b.id)
                );
            }
        ); 

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
};

function collapseAll() {
    expandedKeys.value = {};
};

function expandNode(node: TreeNode) {
    if (node.children && node.children.length) {
        expandedKeys.value[node.key] = true;
        for (const child of node.children) {
            expandNode(child);
        }
    }
};

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
};

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
};

function snoopOnFilterValue() {
    // If we wait to react to the emitted filter event, the templated rows
    // will have already rendered. (<TreeRow> bolds search terms.)
    const inputEl = getInputElement();
    if (inputEl) {
        expandPathsToFilterResults(inputEl.value);
        filterValue.value = inputEl.value;
    }
};

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
};







function findNodeById(data, targetId) {
  const queue = [];
  
  if (Array.isArray(data)) {
    for (const node of data) {
      queue.push({ node, path: [node] });
    }
  } else {
    queue.push({ node: data, path: [data] });
  }

  while (queue.length > 0) {
    const { node: currentNode, path } = queue.shift();

    if (currentNode.id === targetId) {
      return { node: currentNode, path };
    }

    if (currentNode.narrower && Array.isArray(currentNode.narrower)) {
      for (const child of currentNode.narrower) {
        queue.push({ node: child, path: [...path, child] });
      }
    }
  }

  return null;
}

const foo = ref([]);

function selectNodeFromRoute(newRoute: RouteLocationNormalizedLoadedGeneric) {
    if (
        newRoute.name === routeNames.concept &&
        newRoute.params.id === NEW
    ) {
        const schemeId = newRoute.query.scheme;
        const parentId = newRoute.query.parent;

        const schemeToEdit = schemes.value.find(
            (scheme) => scheme.id === schemeId
        );

        let parent;
        let path;

        if (schemeId === parentId) {
            parent = schemeToEdit;
            path = schemeToEdit!.top_concepts;
        } else {
            const result = findNodeById(schemeToEdit!.top_concepts, parentId);
  
            parent = result!.node;
            path = [
                schemeToEdit,
                ...result!.path
            ];
        }

        foo.value = path;

        console.log("((()))", path, parent)

        parent.narrower.unshift(
            {
                id: NEW,
                labels: [
                    {
                        language_id: selectedLanguage.value.code,
                        value: $gettext('New concept'),
                        valuetype_id: "preferred label",
                    }
                ],
                narrower: [],
            }
        )

        schemes.value = schemes.value.map(scheme => {
            if (scheme.id === schemeId) {
                return schemeToEdit!;
            }
            return scheme;
        })

    } else {
        if (foo.value.length) {
            foo.value[foo.value.length - 1].narrower.shift()
            foo.value = [];
        }
    }

    switch (newRoute.name) {
        case routeNames.concept: {
            if (!tree.value.length) {
                return;
            }

            const { found, path } = findNodeInTree(
                tree.value,
                newRoute.params.id as string,
            );
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
            break;
        }
    }
};

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
                    style: instance.node.data.id === NEW
                        ? { backgroundColor: 'red' }
                        : {},
                }
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
        @node-select="(node) => {
            if (node.data.id === NEW) {
                return;
            }

            updateSelectedAndExpanded(node);
            navigateToSchemeOrConcept!(router, node.data);
        }"
    >
        <template #default="slotProps">
            <TreeRow
                :id="slotProps.node.data.id"
                v-model:focused-node="focusedNode"
                :filter-value="filterValue"
                :node="slotProps.node"
                :focus-label="FOCUS"
                :unfocus-label="UNFOCUS"
            />
        </template>
    </Tree>
</template>
