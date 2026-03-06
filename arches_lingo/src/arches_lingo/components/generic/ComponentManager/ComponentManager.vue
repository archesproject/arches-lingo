<script setup lang="ts">
import { computed, markRaw, nextTick, provide, ref } from "vue";

import { useRoute } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useConfirm } from "primevue/useconfirm";

import Splitter from "primevue/splitter";
import SplitterPanel from "primevue/splitterpanel";

import ComponentEditor from "@/arches_lingo/components/generic/ComponentManager/components/ComponentEditor.vue";

import {
    createResourceStore,
    provideResourceStore,
} from "@/arches_lingo/composables/useResourceStore.ts";

import {
    CLOSED,
    EDIT,
    MAXIMIZED,
    MINIMIZED,
    NEW,
    VIEW,
    openPanelComponentKey,
} from "@/arches_lingo/constants.ts";
import {
    useEditorDirtyState,
    unsavedChangesConfirmOptions,
} from "@/arches_lingo/composables/useEditorDirtyState.ts";

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

const route = useRoute();
const { $gettext } = useGettext();
const confirm = useConfirm();
const { isEditorDirty } = useEditorDirtyState();

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
const isFormEditor = ref(true);

const resourceInstanceId = computed<string | undefined>(() => {
    if (route.params.id !== NEW) {
        return route.params.id as string;
    }

    return undefined;
});

const graphSlug = props.componentData[0]?.graphSlug;
const resourceStore = createResourceStore(graphSlug, resourceInstanceId.value);
provideResourceStore(resourceStore);

const firstComponentDatum = computed(() => {
    return processedComponentData.value[0];
});
const remainingComponentData = computed(() => {
    return processedComponentData.value.slice(1);
});

const isConfirmDialogOpen = ref(false);

window.addEventListener(
    "keydown",
    (event) => {
        if (event.key === "Escape" && editorState.value !== CLOSED) {
            if (isConfirmDialogOpen.value) {
                return;
            }
            if (isEditorDirty.value) {
                // Stop propagation so PrimeVue's document-level keydown handler
                // doesn't immediately close the dialog we're about to open.
                event.stopPropagation();
                confirmDiscard(closeEditor);
            } else {
                closeEditor();
            }
        }
    },
    true,
);

function confirmDiscard(callback: () => void) {
    isConfirmDialogOpen.value = true;

    confirm.require({
        ...unsavedChangesConfirmOptions($gettext, () => {
            isConfirmDialogOpen.value = false;
            callback();
        }),
        reject: () => {
            isConfirmDialogOpen.value = false;
        },
        onHide: () => {
            isConfirmDialogOpen.value = false;
        },
    });
}

function closeEditor() {
    selectedComponentDatum.value = null;
    editorState.value = CLOSED;
    editorTileId.value = null;
}

function doOpenEditor(componentName: string, tileId?: string) {
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
    isFormEditor.value = true;
    nextTick(() => {
        isEditorDirty.value = false;
    });
}

function openEditor(componentName: string, tileId?: string) {
    if (editorState.value !== CLOSED && isEditorDirty.value) {
        confirmDiscard(() => doOpenEditor(componentName, tileId));
    } else {
        doOpenEditor(componentName, tileId);
    }
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
        doOpenEditor(componentName);
    }
}

async function refreshReportSection(componentName: string) {
    if (componentName === "all") {
        await resourceStore.refreshResource();
        return;
    }

    const componentDatum = processedComponentData.value.find(
        (componentDatum) => {
            return componentDatum.componentName === componentName;
        },
    );

    if (componentDatum) {
        if (componentDatum.nodegroupAlias) {
            await resourceStore.refreshNodegroup(componentDatum.nodegroupAlias);
        } else {
            await resourceStore.refreshResource();
        }
        componentDatum.key += 1;
    }
}

function openPanelComponent(
    component: Component,
    componentName: string,
    sectionTitle: string,
    graphSlug: string = "",
    nodegroupAlias: string = "",
) {
    selectedComponentDatum.value = {
        component: markRaw(component),
        componentName,
        sectionTitle,
        graphSlug,
        nodegroupAlias,
        key: 0,
    };
    editorKey.value += 1;
    editorTileId.value = null;
    editorState.value = MINIMIZED;
    isFormEditor.value = false;
}

provide("openEditor", openEditor);
provide("closeEditor", closeEditor);
provide("updateAfterComponentDeletion", updateAfterComponentDeletion);
provide("refreshReportSection", refreshReportSection);
provide(openPanelComponentKey, openPanelComponent);
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
                    :is-form-editor="isFormEditor"
                    :header-title="selectedComponentDatum.sectionTitle"
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
                    :is-form-editor="isFormEditor"
                    :header-title="selectedComponentDatum.sectionTitle"
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
    border-color: var(--p-button-primary-active-border-color);
    border-radius: 0.125rem;
    min-width: 11rem;

    &.wide {
        min-width: 14rem;
    }
}

:deep(.concept-header .p-button),
:deep(.scheme-header .p-button) {
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
}

:deep(.concept-header .add-button),
:deep(.scheme-header .add-button) {
    background: var(--p-header-button-background);
    color: var(--p-header-button-color);
    border-color: var(--p-header-button-border);
    border-radius: 0.125rem;
}

:deep(.concept-header .add-button:hover),
:deep(.scheme-header .add-button:hover) {
    background: var(--p-highlight-background);
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
