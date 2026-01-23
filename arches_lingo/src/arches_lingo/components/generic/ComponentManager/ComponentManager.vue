<script setup lang="ts">
import { computed, markRaw, onMounted, provide, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Splitter from "primevue/splitter";
import SplitterPanel from "primevue/splitterpanel";

import ComponentEditor from "@/arches_lingo/components/generic/ComponentManager/components/ComponentEditor.vue";

import {
    CLOSED,
    EDIT,
    MAXIMIZED,
    MINIMIZED,
    NEW,
    VIEW,
} from "@/arches_lingo/constants.ts";

import { fetchResourceInstanceLifecycleState } from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";

import type { Component } from "vue";

const props = defineProps<{
    componentData: {
        component: Component;
        componentName: string;
        sectionTitle: string;
        graphSlug: string;
        nodegroupAlias: string;
    }[];
}>();

const { $gettext } = useGettext();
const toast = useToast();
const route = useRoute();

const processedComponentData = ref(
    props.componentData.map(function (item) {
        return {
            ...item,
            component: markRaw(item.component),
            key: 0,
        };
    }),
);

const editorKey = ref(0);
const editorTileId = ref();
const editorState = ref(CLOSED);
const selectedComponentDatum = ref();

const resourceInstanceLifecycleState = ref<object | undefined>(undefined);
const isFetchingResourceInstanceLifecycleState = ref(false);

const resourceInstanceId = computed<string | undefined>(() => {
    if (route.params.id !== NEW) {
        return route.params.id as string;
    }

    return undefined;
});

const firstComponentDatum = computed(() => {
    return processedComponentData.value[0];
});
const remainingComponentData = computed(() => {
    return processedComponentData.value.slice(1);
});

onMounted(async () => {
    await loadResourceInstanceLifecycleState();
});

watch(resourceInstanceId, async () => {
    await loadResourceInstanceLifecycleState();
});

window.addEventListener("keyup", (event) => {
    if (event.key === "Escape") {
        if (editorState.value !== CLOSED) {
            closeEditor();
        }
    }
});

provide("openEditor", openEditor);
provide("closeEditor", closeEditor);
provide("updateAfterComponentDeletion", updateAfterComponentDeletion);
provide("refreshReportSection", refreshReportSection);
provide("resourceInstanceLifecycleState", resourceInstanceLifecycleState);

function closeEditor() {
    selectedComponentDatum.value = null;
    editorState.value = CLOSED;
    editorTileId.value = null;
}

function openEditor(componentName: string, tileId?: string) {
    const componentDatum = processedComponentData.value.find(
        (componentDatum) => {
            return componentDatum.componentName === componentName;
        },
    );

    if (componentDatum) {
        selectedComponentDatum.value = componentDatum;
    }

    editorKey.value += 1;
    editorTileId.value = tileId;
    editorState.value = MINIMIZED;
}

function maximizeEditor() {
    editorState.value = MAXIMIZED;
}

function minimizeEditor() {
    editorState.value = MINIMIZED;
}

function updateAfterComponentDeletion(componentName: string, tileId: string) {
    if (tileId === editorTileId.value) {
        closeEditor();
        openEditor(componentName);
    }
}

function refreshReportSection(componentName: string) {
    const componentDatum = processedComponentData.value.find(
        (componentDatum) => {
            return componentDatum.componentName === componentName;
        },
    );

    if (componentDatum) {
        componentDatum.key += 1;
    }
}

async function loadResourceInstanceLifecycleState() {
    if (isFetchingResourceInstanceLifecycleState.value) {
        return;
    }

    isFetchingResourceInstanceLifecycleState.value = true;

    try {
        if (!resourceInstanceId.value) {
            resourceInstanceLifecycleState.value = undefined;
            return;
        }

        resourceInstanceLifecycleState.value =
            await fetchResourceInstanceLifecycleState(resourceInstanceId.value);
    } catch (error) {
        resourceInstanceLifecycleState.value = undefined;

        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch lifecycle state"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isFetchingResourceInstanceLifecycleState.value = false;
    }
}
</script>

<template>
    <div class="component-manager">
        <!-- only shown on large screens -->
        <Splitter class="component-splitter component-splitter-horizontal">
            <SplitterPanel
                v-show="editorState !== MAXIMIZED"
                class="content"
                :size="50"
            >
                <div class="splitter-panel-content">
                    <component
                        :is="firstComponentDatum.component"
                        :graph-slug="firstComponentDatum.graphSlug"
                        :nodegroup-alias="firstComponentDatum.nodegroupAlias"
                        :resource-instance-id="resourceInstanceId"
                        :section-title="firstComponentDatum.sectionTitle"
                        :component-name="firstComponentDatum.componentName"
                        :mode="VIEW"
                    />

                    <div class="scroll-container">
                        <component
                            :is="componentDatum.component"
                            v-for="componentDatum in remainingComponentData"
                            :key="
                                componentDatum.componentName +
                                '-' +
                                componentDatum.key
                            "
                            :graph-slug="componentDatum.graphSlug"
                            :nodegroup-alias="componentDatum.nodegroupAlias"
                            :resource-instance-id="resourceInstanceId"
                            :section-title="componentDatum.sectionTitle"
                            :component-name="componentDatum.componentName"
                            :mode="VIEW"
                        />
                    </div>
                </div>
            </SplitterPanel>

            <SplitterPanel
                v-if="editorState !== CLOSED"
                :size="50"
                class="splitter-panel-parent"
            >
                <ComponentEditor
                    :key="editorKey"
                    class="splitter-panel-content"
                    :is-editor-maximized="editorState === MAXIMIZED"
                    @maximize="maximizeEditor"
                    @minimize="minimizeEditor"
                    @close="closeEditor"
                >
                    <component
                        :is="selectedComponentDatum.component"
                        :graph-slug="selectedComponentDatum.graphSlug"
                        :nodegroup-alias="selectedComponentDatum.nodegroupAlias"
                        :resource-instance-id="resourceInstanceId"
                        :tile-id="editorTileId"
                        :section-title="selectedComponentDatum.sectionTitle"
                        :component-name="selectedComponentDatum.componentName"
                        :mode="EDIT"
                    />
                </ComponentEditor>
            </SplitterPanel>
        </Splitter>

        <!-- only shown on small screens -->
        <Splitter
            class="component-splitter component-splitter-vertical"
            layout="vertical"
        >
            <SplitterPanel
                v-show="editorState !== MAXIMIZED"
                class="content"
                :size="50"
            >
                <div class="splitter-panel-content">
                    <component
                        :is="firstComponentDatum.component"
                        :graph-slug="firstComponentDatum.graphSlug"
                        :nodegroup-alias="firstComponentDatum.nodegroupAlias"
                        :resource-instance-id="resourceInstanceId"
                        :section-title="firstComponentDatum.sectionTitle"
                        :component-name="firstComponentDatum.componentName"
                        :mode="VIEW"
                    />

                    <div class="scroll-container">
                        <component
                            :is="componentDatum.component"
                            v-for="componentDatum in remainingComponentData"
                            :key="
                                componentDatum.componentName +
                                '-' +
                                componentDatum.key
                            "
                            :graph-slug="componentDatum.graphSlug"
                            :nodegroup-alias="componentDatum.nodegroupAlias"
                            :resource-instance-id="resourceInstanceId"
                            :section-title="componentDatum.sectionTitle"
                            :component-name="componentDatum.componentName"
                            :mode="VIEW"
                        />
                    </div>
                </div>
            </SplitterPanel>

            <SplitterPanel
                v-if="editorState !== CLOSED"
                :size="50"
                class="splitter-panel-parent"
            >
                <ComponentEditor
                    :key="editorKey"
                    class="splitter-panel-content"
                    :is-editor-maximized="editorState === MAXIMIZED"
                    @maximize="maximizeEditor"
                    @minimize="minimizeEditor"
                    @close="closeEditor"
                >
                    <component
                        :is="selectedComponentDatum.component"
                        :graph-slug="selectedComponentDatum.graphSlug"
                        :nodegroup-alias="selectedComponentDatum.nodegroupAlias"
                        :resource-instance-id="resourceInstanceId"
                        :tile-id="editorTileId"
                        :section-title="selectedComponentDatum.sectionTitle"
                        :component-name="selectedComponentDatum.componentName"
                        :mode="EDIT"
                    />
                </ComponentEditor>
            </SplitterPanel>
        </Splitter>
    </div>
</template>

<style scoped>
.component-manager {
    height: 100%;
    min-height: 0;
}

.component-splitter {
    height: 100%;
    min-height: 0;
    border: none;
}

.component-splitter-horizontal {
    display: flex;
}

.component-splitter-vertical {
    display: none;
}

.content {
    overflow: auto;
}

.splitter-panel-content {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
}

.scroll-container {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
}

:deep(.viewer-section) {
    padding: 1rem 1rem 1.25rem 1rem;
}

:deep(.section-message) {
    padding: 0.5rem 0;
    color: var(--p-inputtext-placeholder-color);
    font-weight: var(--p-lingo-font-weight-light);
}

:deep(.section-header) {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
    padding-bottom: 0.5rem;
}

:deep(.section-header h2) {
    margin: 0;
    font-size: var(--p-lingo-font-size-medium);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-500);
}

:deep(.section-header .add-button) {
    font-size: var(--p-lingo-font-size-xsmall);
    font-weight: var(--p-lingo-font-weight-normal);
    border-color: var(--p-button-primary-border-color);
    border-radius: var(--p-button-border-radius);
    min-width: 11rem;

    &.wide {
        min-width: 14rem;
    }
}

:deep(.concept-header .p-button),
:deep(.scheme-header .p-button) {
    font-size: var(--p-lingo-font-size-small);
}

:deep(.concept-header .add-button),
:deep(.scheme-header .add-button) {
    background: var(--p-header-button-background);
    color: var(--p-header-button-color);
    border-color: var(--p-header-button-border);
}

.p-splitter .p-splitterpanel .splitter-panel-content .p-skeleton {
    min-height: 9rem;
    margin-top: 1rem;
}

:deep(
        .component-splitter-horizontal
            .p-splitterpanel:has(> .splitter-panel-content)
    ) {
    overflow-y: auto;
    width: 12rem;
}

@media (max-width: 960px) {
    .component-splitter-horizontal {
        display: none;
    }

    .component-splitter-vertical {
        display: flex;
    }
}
</style>
