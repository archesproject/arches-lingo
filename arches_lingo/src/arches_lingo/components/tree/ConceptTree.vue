<script setup lang="ts">
import {
    computed,
    inject,
    nextTick,
    onMounted,
    provide,
    reactive,
    ref,
    watch,
} from "vue";
import type { Ref } from "vue";
import Button from "primevue/button";

import {
    useRoute,
    useRouter,
    isNavigationFailure,
    NavigationFailureType,
} from "vue-router";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";
import { storeToRefs } from "pinia";
import Skeleton from "primevue/skeleton";
import InputText from "primevue/inputtext";
import Message from "primevue/message";

import Tree from "primevue/tree";

import TreeRow from "@/arches_lingo/components/tree/components/TreeRow/TreeRow.vue";

import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
} from "@/arches_controlled_lists/constants.ts";
import { RETIRED_LIFECYCLE_STATE_ID } from "@/arches_lingo/constants.ts";

import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";
import { fetchLifecycleStates } from "@/arches_lingo/api.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

import {
    treeFromSchemes,
    navigateToSchemeOrConcept,
    filterTreeByLifecycleStates,
} from "@/arches_lingo/utils.ts";

import { useCappedTreeFilter } from "@/arches_lingo/components/tree/utils/capped-filter.ts";
import LifecycleStateFilter from "@/arches_lingo/components/tree/components/LifecycleStateFilter.vue";

import type {
    TreePassThroughMethodOptions,
    TreeExpandedKeys,
    TreeSelectionKeys,
} from "primevue/tree";
import type { TreeNode } from "primevue/treenode";
import type {
    IconLabels,
    LifecycleState,
    Scheme,
    Concept,
    ResourceInstanceLifecycleState,
} from "@/arches_lingo/types";

const props = withDefaults(
    defineProps<{
        isOpen?: boolean;
    }>(),
    {
        isOpen: true,
    },
);

const resourceInstanceLifecycleStates = inject<
    Ref<ResourceInstanceLifecycleState[] | undefined>
>("resourceInstanceLifecycleStates");

const toast = useToast();
const { $gettext } = useGettext();
const route = useRoute();
const router = useRouter();

const NEW = "new";
const FOCUS = computed(() => $gettext("Focus"));
const UNFOCUS = computed(() => $gettext("Unfocus"));
const ADD_CHILD = computed(() => $gettext("Add child"));
const DELETE = computed(() => $gettext("Delete"));
const EXPORT = computed(() => $gettext("Export"));

const FILTER_CONCEPTS = computed(() => $gettext("Filter concepts"));
const FILTER_CAPPED_MESSAGE = computed(() =>
    $gettext("Please refine your query."),
);
const SORT_ASCENDING = computed(() => $gettext("Sort ascending"));
const SORT_DESCENDING = computed(() => $gettext("Sort descending"));

const iconLabels = computed<IconLabels>(() =>
    Object.freeze({
        concept: $gettext("Concept"),
        guideTerm: $gettext("Guide Term"),
        scheme: $gettext("Scheme"),
        topConcept: $gettext("Top Concept"),
    }),
);

const schemes = ref<Scheme[]>([]);
const shouldSortByAscending = ref(route.query.sort !== "desc");
const focusedNode = ref<TreeNode | null>(null);
const focusedOccurrenceKey = ref<string | null>(null);

const selectedKeys = ref<TreeSelectionKeys>({});
const lastNonEmptySelectedKeys = ref<TreeSelectionKeys>({});
const expandedKeys = ref<TreeExpandedKeys>({});
const filterValue = ref((route.query.filter as string) ?? "");
const lifecycleStates = ref<LifecycleState[]>([]);
const selectedLifecycleStateIds = ref<string[]>(getInitialLifecycleStateIds());

const FILTER_RENDER_CAP = 2500;
const FILTER_DEBOUNCE_MS = 500;
const SKELETON_ROW_COUNT = 14;

const suppressScrollOnNextRouteSelect = ref(false);
const hasCompletedInitialLoad = ref(false);

const conceptStore = useConceptStore();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

onMounted(async () => {
    try {
        await conceptStore.initialize();
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch concepts"),
            detail: (error as Error).message,
        });
    }

    try {
        lifecycleStates.value = await fetchLifecycleStates();

        if (!route.query.lifecycle) {
            selectedLifecycleStateIds.value = lifecycleStates.value.map(
                (state) => state.id,
            );
        }
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch lifecycle states"),
            detail: (error as Error).message,
        });
    }

    const priorSortedSchemeIds = tree.value.map((treeNode) => treeNode.key);

    schemes.value = [...conceptStore.schemes].sort((schemeA, schemeB) => {
        return (
            priorSortedSchemeIds.indexOf(schemeA.id) -
            priorSortedSchemeIds.indexOf(schemeB.id)
        );
    });

    await nextTick();
    await selectNodeFromRoute(route, false);

    if (props.isOpen) {
        await handleTreeOpened();
    }

    hasCompletedInitialLoad.value = true;
});

const resourceInstanceLifecycleStateCanEditById = computed(() =>
    Object.fromEntries(
        (resourceInstanceLifecycleStates?.value ?? []).map(
            (
                resourceInstanceLifecycleState: ResourceInstanceLifecycleState,
            ) => [
                resourceInstanceLifecycleState.id,
                resourceInstanceLifecycleState.can_edit_resource_instances ===
                    true,
            ],
        ),
    ),
);

const resourceInstanceLifecycleStateIsRetiredById = computed(() =>
    Object.fromEntries(
        (resourceInstanceLifecycleStates?.value ?? []).map(
            (state: ResourceInstanceLifecycleState) => [
                state.id,
                state.id === RETIRED_LIFECYCLE_STATE_ID,
            ],
        ),
    ),
);

provide(
    "resourceInstanceLifecycleStateCanEditById",
    resourceInstanceLifecycleStateCanEditById,
);

provide(
    "resourceInstanceLifecycleStateIsRetiredById",
    resourceInstanceLifecycleStateIsRetiredById,
);

// Tracks concept IDs whose children are currently being fetched so the tree
// can show a loading indicator on the relevant expand toggle.
const loadingConceptIds = reactive(new Set<string>());
provide("loadingConceptIds", loadingConceptIds);

const sortIcon = computed(() => {
    const direction = shouldSortByAscending.value ? "down" : "up";
    return `pi pi-sort-alpha-${direction}`;
});

const tree = computed(() => {
    return treeFromSchemes(
        schemes.value,
        selectedLanguage.value,
        systemLanguage.value,
        iconLabels.value,
        focusedOccurrenceKey.value,
        shouldSortByAscending.value,
    );
});

const lifecycleStateFilteredTree = computed(() => {
    const ids = selectedLifecycleStateIds.value;
    const total = lifecycleStates.value.length;

    if (total === 0 || ids.length >= total) {
        return tree.value;
    }
    if (ids.length === 0) {
        return [];
    }
    return filterTreeByLifecycleStates(tree.value, new Set(ids));
});

const { debouncedFilterValue, filteredTree, isFilterCapped } =
    useCappedTreeFilter(
        lifecycleStateFilteredTree,
        expandedKeys,
        filterValue,
        FILTER_DEBOUNCE_MS,
        FILTER_RENDER_CAP,
        getSearchableText,
    );

const displayTree = computed<TreeNode[]>(() => {
    const parentKeyToNewChild = new Map<string, TreeNode>();
    const sourceQueue = [...tree.value];

    for (const currentSourceNode of sourceQueue) {
        const sourceChildren = (currentSourceNode.children ?? []) as TreeNode[];

        const sourceNewChild = sourceChildren.find(
            (childNode) => childNode.data.id === NEW,
        );

        if (sourceNewChild) {
            parentKeyToNewChild.set(currentSourceNode.key, sourceNewChild);
        }

        sourceQueue.push(...sourceChildren);
    }

    const filteredQueue = [...filteredTree.value];

    for (const currentFilteredNode of filteredQueue) {
        const newChildFromSource = parentKeyToNewChild.get(
            currentFilteredNode.key,
        );

        if (newChildFromSource) {
            const currentChildren = (currentFilteredNode.children ??
                []) as TreeNode[];
            const alreadyHasNew = currentChildren.some(
                (childNode) => childNode.data.id === NEW,
            );

            if (!alreadyHasNew) {
                currentFilteredNode.children = [
                    newChildFromSource,
                    ...currentChildren,
                ];
            }
        }

        filteredQueue.push(
            ...((currentFilteredNode.children ?? []) as TreeNode[]),
        );
    }

    return filteredTree.value;
});

watch(
    () => route.path,
    async () => {
        const shouldScroll = !suppressScrollOnNextRouteSelect.value;
        suppressScrollOnNextRouteSelect.value = false;

        await selectNodeFromRoute(route, shouldScroll);
    },
);

watch([() => route.query.scheme, () => route.query.parent], async () => {
    if (route.params.id !== NEW) return;
    await selectNodeFromRoute(route, true);
});

watch(debouncedFilterValue, (currentFilter) => {
    router.replace({
        query: { ...route.query, filter: currentFilter || undefined },
    });
});

watch(shouldSortByAscending, (isAscending) => {
    router.replace({
        query: { ...route.query, sort: isAscending ? undefined : "desc" },
    });
});

watch(
    () => route.query.filter,
    (queryFilter) => {
        filterValue.value = (queryFilter as string) ?? "";
    },
);

watch(
    () => route.query.sort,
    (querySort) => {
        shouldSortByAscending.value = querySort !== "desc";
    },
);

watch(selectedLifecycleStateIds, (ids) => {
    const total = lifecycleStates.value.length;
    let lifecycleParam: string | undefined;

    if (ids.length === 0) {
        lifecycleParam = "none";
    } else if (ids.length >= total && total > 0) {
        lifecycleParam = undefined;
    } else {
        lifecycleParam = ids.join(",");
    }

    router.replace({
        query: { ...route.query, lifecycle: lifecycleParam },
    });
});

watch(
    () => route.query.lifecycle,
    (queryLifecycle) => {
        let newIds: string[];

        if (queryLifecycle === "none") {
            newIds = [];
        } else if (queryLifecycle) {
            newIds = (queryLifecycle as string).split(",");
        } else {
            newIds = lifecycleStates.value.map(
                (lifecycleState) => lifecycleState.id,
            );
        }

        if (newIds.join(",") === selectedLifecycleStateIds.value.join(",")) {
            return;
        }

        selectedLifecycleStateIds.value = newIds;
    },
);

watch(
    () => props.isOpen,
    async (nextIsOpen) => {
        if (!nextIsOpen) {
            return;
        }

        await handleTreeOpened();
    },
);

watch(
    selectedKeys,
    (nextSelectedKeys) => {
        if (Object.keys(nextSelectedKeys).length) {
            lastNonEmptySelectedKeys.value = nextSelectedKeys;
            return;
        }

        if (Object.keys(lastNonEmptySelectedKeys.value).length) {
            selectedKeys.value = lastNonEmptySelectedKeys.value;
        }
    },
    { deep: true },
);

watch(focusedNode, async (nextFocusedNode, previousFocusedNode) => {
    if (!props.isOpen) {
        return;
    }

    if (!previousFocusedNode && nextFocusedNode) {
        focusedOccurrenceKey.value = nextFocusedNode.key;

        await nextTick();
        scrollToOccurrenceKeyInTree(nextFocusedNode.key, false);
        await ensureFilterParentsExpanded();
        return;
    }

    if (previousFocusedNode && !nextFocusedNode) {
        const priorOccurrenceKey = previousFocusedNode.key;

        focusedOccurrenceKey.value = null;

        await nextTick();
        scrollToOccurrenceKeyInTree(priorOccurrenceKey, true);
        await ensureFilterParentsExpanded();
    }
});

watch(
    debouncedFilterValue,
    async (nextDebouncedFilterValue, previousDebouncedFilterValue) => {
        if (previousDebouncedFilterValue && !nextDebouncedFilterValue) {
            if (!props.isOpen) {
                return;
            }

            await nextTick();
            scrollToItemInTree(
                (route.meta.resolvedResourceId as string) ||
                    (route.params.id as string),
                true,
            );
            return;
        }

        if (!nextDebouncedFilterValue) {
            return;
        }

        await nextTick();
        expandVisibleParentsWithNewChild(displayTree.value);
    },
    { flush: "post" },
);

function getInitialLifecycleStateIds(): string[] {
    if (route.query.lifecycle === "none") {
        return [];
    }
    if (route.query.lifecycle) {
        return (route.query.lifecycle as string).split(",");
    }
    return [];
}

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

function setExpandedKeysToOnly(theseExpandedKeys: Set<string>) {
    expandedKeys.value = Object.fromEntries(
        [...theseExpandedKeys].map((expandedKey) => [expandedKey, true]),
    ) as TreeExpandedKeys;
}

function mergeExpandedKeys(keysToAdd: Set<string>) {
    expandedKeys.value = {
        ...expandedKeys.value,
        ...Object.fromEntries([...keysToAdd].map((key) => [key, true])),
    } as TreeExpandedKeys;
}

function findAllNewOccurrencesInTree() {
    const foundOccurrences: Array<{
        occurrenceKey: string;
        pathKeys: string[];
    }> = [];

    const matchQueue = tree.value.map((rootTreeNode) => ({
        treeNode: rootTreeNode,
        path: [rootTreeNode],
    }));

    for (const matchItem of matchQueue) {
        const currentTreeNode = matchItem.treeNode;
        const currentPath = matchItem.path;

        if (currentTreeNode.data.id === NEW) {
            const pathKeys = currentPath.map((pathNode) => pathNode.key);
            const parentPathKeys = pathKeys.slice(
                0,
                Math.max(0, pathKeys.length - 1),
            );

            foundOccurrences.push({
                occurrenceKey: currentTreeNode.key,
                pathKeys: parentPathKeys,
            });
        }

        const children = (currentTreeNode.children ?? []) as TreeNode[];
        matchQueue.push(
            ...children.map((childNode) => ({
                treeNode: childNode,
                path: [...currentPath, childNode],
            })),
        );
    }

    return foundOccurrences;
}

function scrollOccurrenceIntoView(occurrenceKey: string) {
    nextTick(() => {
        document
            .getElementById(`tree-node-${occurrenceKey}`)
            ?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
}

function expandAndSelectOccurrences(
    newOccurrences: Array<{ occurrenceKey: string; pathKeys: string[] }>,
) {
    const keysToExpand = new Set<string>();

    for (const occurrenceItem of newOccurrences) {
        for (const pathKey of occurrenceItem.pathKeys) {
            keysToExpand.add(pathKey);
        }
        keysToExpand.add(occurrenceItem.occurrenceKey);
    }

    setExpandedKeysToOnly(keysToExpand);
    selectedKeys.value = { [newOccurrences[0].occurrenceKey]: true };
}

function expandVisibleParentsWithNewChild(treeNodes: TreeNode[]) {
    const keysToExpand = new Set<string>();
    const queue = [...treeNodes];

    for (const currentNode of queue) {
        const children = currentNode.children ?? [];

        if (children.some((childNode) => childNode.data.id === NEW)) {
            keysToExpand.add(currentNode.key);
        }

        queue.push(...children);
    }

    if (!keysToExpand.size) {
        return;
    }

    expandedKeys.value = {
        ...expandedKeys.value,
        ...Object.fromEntries(
            [...keysToExpand].map((keyItem) => [keyItem, true]),
        ),
    };
}

async function ensureFilterParentsExpanded() {
    if (!debouncedFilterValue.value) {
        return;
    }

    await nextTick();
    expandVisibleParentsWithNewChild(displayTree.value);
}

async function handleTreeOpened() {
    await nextTick();

    const newOccurrences = findAllNewOccurrencesInTree();

    if (newOccurrences.length) {
        expandAndSelectOccurrences(newOccurrences);
        await nextTick();
        scrollOccurrenceIntoView(newOccurrences[0].occurrenceKey);
        return;
    }

    scrollToItemInTree(route.params.id as string, true);
}

function scrollToOccurrenceKeyInTree(
    occurrenceKey: string,
    shouldScroll: boolean,
) {
    const matchQueue = tree.value.map((rootTreeNode) => ({
        treeNode: rootTreeNode,
        path: [rootTreeNode],
    }));

    for (const matchItem of matchQueue) {
        const currentTreeNode = matchItem.treeNode;
        const currentPath = matchItem.path;

        if (currentTreeNode.key === occurrenceKey) {
            const keysToExpand = new Set<string>();

            for (const pathNode of currentPath) {
                keysToExpand.add(pathNode.key);
            }

            keysToExpand.add(occurrenceKey);
            mergeExpandedKeys(keysToExpand);

            selectedKeys.value = { [occurrenceKey]: true };

            if (shouldScroll) {
                scrollOccurrenceIntoView(occurrenceKey);
            }

            return;
        }

        const children = currentTreeNode.children ?? [];
        matchQueue.push(
            ...children.map((childNode) => ({
                treeNode: childNode,
                path: [...currentPath, childNode],
            })),
        );
    }
}

function removeAllNewNodes() {
    for (const schemeItem of schemes.value) {
        schemeItem.top_concepts = (schemeItem.top_concepts ?? []).filter(
            (conceptItem) => conceptItem.id !== NEW,
        );

        const traversalQueue = [...(schemeItem.top_concepts ?? [])];

        for (const currentConcept of traversalQueue) {
            currentConcept.narrower = (currentConcept.narrower ?? []).filter(
                (childConcept) => childConcept.id !== NEW,
            );

            traversalQueue.push(...(currentConcept.narrower ?? []));
        }
    }
}

function addNewConceptToTree(schemeId: string, parentId: string) {
    const targetScheme = schemes.value.find(
        (schemeItem) => schemeItem.id === schemeId,
    );

    if (!targetScheme) {
        return;
    }

    const newConcept: Concept = {
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

    if (schemeId === parentId) {
        targetScheme.top_concepts = targetScheme.top_concepts ?? [];

        const alreadyHasNew = targetScheme.top_concepts.some(
            (conceptItem) => conceptItem.id === NEW,
        );

        if (!alreadyHasNew) {
            targetScheme.top_concepts.unshift(newConcept);
        }

        schemes.value = schemes.value.map((existingScheme) => {
            return existingScheme.id === schemeId
                ? targetScheme
                : existingScheme;
        });

        return;
    }

    const visitedConceptObjects = new Set<Concept>();
    const traversalQueue = [...(targetScheme.top_concepts ?? [])];

    for (const currentConcept of traversalQueue) {
        if (visitedConceptObjects.has(currentConcept)) {
            continue;
        }

        visitedConceptObjects.add(currentConcept);

        if (currentConcept.id === parentId) {
            currentConcept.narrower = currentConcept.narrower ?? [];

            const alreadyHasNew = currentConcept.narrower.some(
                (childConcept) => childConcept.id === NEW,
            );

            if (!alreadyHasNew) {
                currentConcept.narrower.unshift(newConcept);
            }
        }

        traversalQueue.push(...(currentConcept.narrower ?? []));
    }

    schemes.value = schemes.value.map((existingScheme) => {
        return existingScheme.id === schemeId ? targetScheme : existingScheme;
    });
}

function scrollToItemInTree(
    nodeId: string,
    shouldScroll: boolean,
    preferredOccurrenceKey?: string,
) {
    const matchQueue = tree.value.map((rootTreeNode) => ({
        treeNode: rootTreeNode,
        path: [rootTreeNode],
    }));

    const matches: Array<{ treeNode: TreeNode; path: TreeNode[] }> = [];

    for (const matchItem of matchQueue) {
        const currentTreeNode = matchItem.treeNode;
        const currentPath = matchItem.path;

        if (currentTreeNode.data.id === nodeId) {
            matches.push({ treeNode: currentTreeNode, path: currentPath });
        }

        const children = currentTreeNode.children ?? [];
        matchQueue.push(
            ...children.map((childNode) => ({
                treeNode: childNode,
                path: [...currentPath, childNode],
            })),
        );
    }

    if (!matches.length) {
        return;
    }

    const keysToExpand = new Set<string>();
    for (const matchItem of matches) {
        for (const pathNode of matchItem.path) {
            keysToExpand.add(pathNode.key);
        }
        keysToExpand.add(matchItem.treeNode.key);
    }

    if (!debouncedFilterValue.value) {
        mergeExpandedKeys(keysToExpand);
    }

    const matchedKeysInOrder = matches.map(
        (matchItem) => matchItem.treeNode.key,
    );

    const currentSelectedPrimaryKey = Object.keys(selectedKeys.value)[0];
    const preferredIsValid =
        preferredOccurrenceKey &&
        matchedKeysInOrder.includes(preferredOccurrenceKey);

    const retainedIsValid =
        !shouldScroll &&
        currentSelectedPrimaryKey &&
        matchedKeysInOrder.includes(currentSelectedPrimaryKey);

    let primaryOccurrenceKey = matchedKeysInOrder[0];

    if (retainedIsValid) {
        primaryOccurrenceKey = currentSelectedPrimaryKey!;
    }
    if (preferredIsValid) {
        primaryOccurrenceKey = preferredOccurrenceKey!;
    }

    const orderedSelectedKeys = [
        primaryOccurrenceKey,
        ...matchedKeysInOrder.filter(
            (keyItem) => keyItem !== primaryOccurrenceKey,
        ),
    ];

    selectedKeys.value = Object.fromEntries(
        orderedSelectedKeys.map((keyItem) => [keyItem, true]),
    );

    if (!shouldScroll) {
        return;
    }

    scrollOccurrenceIntoView(primaryOccurrenceKey);
}

async function selectNodeFromRoute(
    newRoute: typeof route,
    shouldScroll: boolean,
) {
    const routeNodeId =
        (newRoute.meta.resolvedResourceId as string) ||
        (newRoute.params.id as string);

    removeAllNewNodes();

    if (routeNodeId === NEW) {
        addNewConceptToTree(
            newRoute.query.scheme as string,
            newRoute.query.parent as string,
        );

        await nextTick();

        if (hasCompletedInitialLoad.value && props.isOpen) {
            await handleTreeOpened();
        }

        await ensureFilterParentsExpanded();
        return;
    }

    const priorSelectedPrimaryKey = Object.keys(selectedKeys.value)[0] ?? null;

    let preferredOccurrenceKey: string | undefined;
    if (!shouldScroll) {
        preferredOccurrenceKey = priorSelectedPrimaryKey ?? undefined;
    }

    scrollToItemInTree(routeNodeId, shouldScroll, preferredOccurrenceKey);

    await ensureFilterParentsExpanded();
}

async function onNodeSelect(node: TreeNode) {
    if (node.data.id === NEW) return;

    const selectedKeysBeforeNavigation = { ...selectedKeys.value };

    await nextTick();
    scrollToItemInTree(node.data.id, false);

    suppressScrollOnNextRouteSelect.value = true;
    const navigationResult = await navigateToSchemeOrConcept(router, node.data);

    if (!isNavigationFailure(navigationResult)) return;

    suppressScrollOnNextRouteSelect.value = false;

    if (isNavigationFailure(navigationResult, NavigationFailureType.duplicated))
        return;

    selectedKeys.value = selectedKeysBeforeNavigation;
    const primaryOriginalKey = Object.keys(selectedKeysBeforeNavigation)[0];

    if (primaryOriginalKey) {
        scrollOccurrenceIntoView(primaryOriginalKey);
    }
}

async function onNodeExpand(node: TreeNode) {
    const conceptId: string = node.data?.id;
    if (!conceptId || node.data?.top_concepts !== undefined) return;

    const concept = conceptStore.findConcept(conceptId);
    if (!concept || concept.childrenLoaded) return;

    loadingConceptIds.add(conceptId);
    try {
        await conceptStore.loadChildren(conceptId);
    } catch {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch concepts"),
            detail: $gettext("Failed to load child concepts."),
        });
    } finally {
        loadingConceptIds.delete(conceptId);
    }
}
</script>

<template>
    <div class="concept-tree-layout">
        <div class="filter-container">
            <div class="filter-toolbar">
                <InputText
                    v-model="filterValue"
                    class="tree-filter-input"
                    type="text"
                    :placeholder="FILTER_CONCEPTS"
                    :aria-label="FILTER_CONCEPTS"
                />
                <Button
                    :icon="sortIcon"
                    :aria-label="
                        shouldSortByAscending ? SORT_ASCENDING : SORT_DESCENDING
                    "
                    variant="text"
                    size="small"
                    @click="shouldSortByAscending = !shouldSortByAscending"
                />
                <LifecycleStateFilter
                    v-model:selected-lifecycle-state-ids="
                        selectedLifecycleStateIds
                    "
                    :lifecycle-states="lifecycleStates"
                />
            </div>
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
            :value="displayTree"
            class="concept-tree"
            selection-mode="single"
            :pt="{
                nodeContent: ({ instance }: TreePassThroughMethodOptions) => {
                    let className;

                    if (instance.node.data.id === NEW) {
                        className = 'new-node';
                    }

                    return { class: className };
                },
                nodeIcon: ({ instance }: TreePassThroughMethodOptions) => {
                    return { ariaLabel: instance.node.iconLabel };
                },
                nodeLabel: {
                    style: { textWrap: 'nowrap' },
                },
                nodeToggleButton: ({
                    instance,
                }: TreePassThroughMethodOptions) => ({
                    class: {
                        'node-children-loading': loadingConceptIds.has(
                            instance.node?.data?.id,
                        ),
                    },
                }),
            }"
            @node-select="onNodeSelect"
            @node-expand="onNodeExpand"
        >
            <template #default="slotProps">
                <div :id="`tree-node-${slotProps.node.key}`">
                    <TreeRow
                        :id="slotProps.node.data.id"
                        v-model:focused-node="focusedNode"
                        :filter-value="
                            isFilterCapped ? '' : debouncedFilterValue
                        "
                        :node="slotProps.node"
                        :focus-label="FOCUS"
                        :unfocus-label="UNFOCUS"
                        :add-child-label="ADD_CHILD"
                        :delete-label="DELETE"
                        :export-label="EXPORT"
                    />
                </div>
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
    padding-top: 0;
    padding-inline: 1rem;
    padding-bottom: 1rem;
    background: var(--p-header-toolbar-background);
    border-bottom: 0.0625rem solid var(--p-menubar-border-color);
    margin-bottom: 0.5rem;
}

.filter-toolbar {
    display: flex;
    align-items: center;
    gap: 0.25rem;
}

.tree-filter-input {
    border-radius: 0.125rem;
    flex: 1;
    font-size: 0.875rem;
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

:deep(.p-tree-node-content) {
    width: fit-content;
}

:deep(.p-tree-node-content) {
    border-radius: 0.25rem !important;
}

:deep(.p-tree-node-selected) {
    background: var(--p-header-button-background) !important;
    color: var(--p-header-button-color) !important;
}

:deep(.p-tree-node-selected .p-tree-node-icon) {
    color: var(--p-header-button-color) !important;
}

:deep(.p-tree-node-selected button) {
    color: var(--p-header-button-color) !important;
}

:deep(.p-tree-node-selected button:hover) {
    background: var(--p-header-button-background) !important;
}

:deep(.p-tree-node-selected.new-node) {
    background: var(--p-yellow-500) !important;
}

/* Spin the expand toggle icon while children are being fetched */
:deep(.node-children-loading .p-tree-node-toggle-icon) {
    animation: tree-toggle-spin 0.6s linear infinite;
    pointer-events: none;
}

@keyframes tree-toggle-spin {
    from {
        transform: rotate(0deg);
    }
    to {
        transform: rotate(360deg);
    }
}
</style>
