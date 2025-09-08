<script setup lang="ts">
import { computed, markRaw, provide, ref } from "vue";

import { useRoute } from "vue-router";

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

window.addEventListener("keyup", (event) => {
    if (event.key === "Escape") {
        if (editorState.value !== CLOSED) {
            closeEditor();
        }
    }
});

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

provide("openEditor", openEditor);
provide("closeEditor", closeEditor);
provide("updateAfterComponentDeletion", updateAfterComponentDeletion);
provide("refreshReportSection", refreshReportSection);
</script>

<template>
    <Splitter style="height: 100%; min-height: 0; border-radius: 0">
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
</template>

<style scoped>
.content {
    overflow: auto;
}

.splitter-panel-content {
    display: flex;
    flex-direction: column;
    height: 100%;
}

.scroll-container {
    flex: 1;
    overflow-y: auto;
}

:deep(.p-splitter) {
    border-radius: 0;
}

:deep(.viewer-section) {
    padding: 1rem 1rem 1.25rem 1rem;
}

:deep(.section-message) {
    padding: 0.5rem 0;
    color: var(--p-inputtext-placeholder-color);
}

:deep(.section-header) {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 0.06rem solid var(--p-highlight-focus-background);
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
    border-color: var(--p-header-button-border);
    min-width: 10rem;
    border-radius: 0.125rem;
    padding: 0.5rem 0rem;
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

.p-splitterpanel:has(> .splitter-panel-content) {
    overflow-y: auto;
    width: 12rem;
}
</style>
