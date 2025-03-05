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
        componentDatum.key += 1;
    }

    editorTileId.value = tileId;
    editorState.value = MINIMIZED;
}

function maximizeEditor() {
    editorState.value = MAXIMIZED;
}

function minimizeEditor() {
    editorState.value = MINIMIZED;
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
provide("refreshReportSection", refreshReportSection);
</script>

<template>
    <Splitter style="height: 100%">
        <SplitterPanel
            v-show="editorState !== MAXIMIZED"
            :size="66"
            style="overflow: auto"
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
            :size="editorState === MINIMIZED ? 33 : 100"
        >
            <ComponentEditor
                :is-editor-maximized="editorState === MAXIMIZED"
                @maximize="maximizeEditor"
                @minimize="minimizeEditor"
                @close="closeEditor"
            >
                <component
                    :is="selectedComponentDatum.component"
                    :key="
                        selectedComponentDatum.componentName +
                        '-' +
                        selectedComponentDatum.key
                    "
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
