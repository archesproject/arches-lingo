<script setup lang="ts">
import { computed, inject, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import Tree from "primevue/tree";

import { getItemLabel } from "@/arches_vue_utils/utils.ts";
import PresentationControls from "@/arches_references/components/tree/PresentationControls.vue";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
} from "@/arches_references/constants.ts";
import { findNodeInTree } from "@/arches_references/utils.ts";
import { fetchConcepts } from "@/arches_lingo/api.ts";
import {
    displayedRowKey,
    selectedLanguageKey,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";
import { treeFromSchemes } from "@/arches_lingo/utils.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import LetterCircle from "@/arches_lingo/components/misc/LetterCircle.vue";
import TreeRow from "@/arches_lingo/components/tree/TreeRow.vue";

import type { ComponentPublicInstance, Ref } from "vue";
import type { RouteLocationNormalizedLoadedGeneric } from "vue-router";
import type { TreeExpandedKeys, TreeSelectionKeys } from "primevue/tree";
import type { TreeNode } from "primevue/treenode";
import type { Language } from "@/arches_vue_utils/types";
import type {
    DisplayedRowRefAndSetter,
    IconLabels,
    Scheme,
} from "@/arches_lingo/types";

const toast = useToast();
const { $gettext } = useGettext();
const route = useRoute();

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
const { setDisplayedRow } = inject(
    displayedRowKey,
) as unknown as DisplayedRowRefAndSetter;

const tree = computed(() =>
    treeFromSchemes(
        schemes.value,
        selectedLanguage.value,
        systemLanguage,
        iconLabels,
        focusedNode.value,
    ),
);

const navigate = (newRoute: RouteLocationNormalizedLoadedGeneric) => {
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
                setDisplayedRow(found.data);
                const itemsToExpandIds = path.map(
                    (itemInPath: TreeNode) => itemInPath.key,
                );
                expandedKeys.value = {
                    ...expandedKeys.value,
                    ...Object.fromEntries(
                        itemsToExpandIds.map((x) => [x, true]),
                    ),
                };
                selectedKeys.value = { [found.data.id]: true };
            }
            break;
        }
    }
};

// React to route changes.
watch(
    [
        () => {
            return { ...route };
        },
    ],
    ([newRoute]) => {
        navigate(newRoute);
    },
);

// Navigate on initial load of the tree.
watch(tree, () => navigate(route), { once: true });

const expandAll = () => {
    for (const node of tree.value) {
        expandNode(node);
    }
    expandedKeys.value = { ...expandedKeys.value };
};

const collapseAll = () => {
    expandedKeys.value = {};
};

const expandNode = (node: TreeNode) => {
    if (node.children && node.children.length) {
        expandedKeys.value[node.key] = true;
        for (const child of node.children) {
            expandNode(child);
        }
    }
};

const expandPathsToFilterResults = (newFilterValue: string) => {
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

const restoreFocusToInput = () => {
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

const snoopOnFilterValue = () => {
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

const updateSelectedAndExpanded = (node: TreeNode) => {
    setDisplayedRow(node.data);
    expandedKeys.value = {
        ...expandedKeys.value,
        [node.key]: true,
    };
};

const initializeTree = async () => {
    /*
    Currently, rather than inspecting the results of the batched
    delete requests, we just refetch everything. This requires being
    a little clever about resorting the ordered response from the API
    to preserve the existing sort (and avoid confusion).
    */
    const priorSortedSchemeIds = tree.value.map((node) => node.key);

    await fetchConcepts()
        .then(({ schemes: fetchedSchemes }: { schemes: Scheme[] }) => {
            schemes.value = fetchedSchemes.sort(
                (a, b) =>
                    priorSortedSchemeIds.indexOf(a.id) -
                    priorSortedSchemeIds.indexOf(b.id),
            );
        })
        .catch((error: Error) => {
            toast.add({
                severity: ERROR,
                life: DEFAULT_ERROR_TOAST_LIFE,
                summary: $gettext("Unable to fetch concepts"),
                detail: error.message,
            });
        });
};

await initializeTree();
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
            pcFilterIconContainer: {
                root: {
                    style: { top: '30%' },
                },
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
        @node-select="updateSelectedAndExpanded"
    >
        <template #nodeicon="slotProps">
            <LetterCircle :labelled="slotProps.node.data" />
        </template>
        <template #default="slotProps">
            <TreeRow
                v-model:focused-node="focusedNode"
                v-model:filter-value="filterValue"
                :node="slotProps.node"
                :focus-label="FOCUS"
                :unfocus-label="UNFOCUS"
            />
        </template>
    </Tree>
</template>
