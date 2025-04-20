<script setup lang="ts">
import { computed, inject, markRaw, provide, ref } from "vue";

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
import type { HierarchyRefAndSetter } from "@/arches_lingo/types";

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
const toggleHierarchy = inject<HierarchyRefAndSetter>("toggleHierarchy");

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

    if (toggleHierarchy?.hierarchyVisible.value) {
        toggleHierarchy.toggleHierarchy();
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
provide("updateAfterComponentDeletion", updateAfterComponentDeletion);
provide("refreshReportSection", refreshReportSection);
</script>

<template>
    <Splitter style="height: 100%">
        <SplitterPanel
            v-show="editorState !== MAXIMIZED"
            :size="30"
            class="splitter-panel"
        >
            <component
                :is="componentDatum.component"
                v-for="componentDatum in processedComponentData"
                :key="componentDatum.componentName + '-' + componentDatum.key"
                :graph-slug="componentDatum.graphSlug"
                :nodegroup-alias="componentDatum.nodegroupAlias"
                :resource-instance-id="resourceInstanceId"
                :section-title="componentDatum.sectionTitle"
                :component-name="componentDatum.componentName"
                :mode="VIEW"
            />
        </SplitterPanel>

        <SplitterPanel
            v-if="editorState !== CLOSED"
            :size="editorState === MINIMIZED ? 70 : 100"
            class="splitter-panel"
        >
            <ComponentEditor
                :key="editorKey"
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
.splitter-panel {
    overflow: auto;
    padding: 0rem 1rem 1rem 1rem;
}
</style>
