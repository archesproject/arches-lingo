<script setup lang="ts">
import { computed, markRaw, provide, ref } from "vue";

import { useGettext } from "vue3-gettext";
import { useRoute } from "vue-router";

import Splitter from "primevue/splitter";
import SplitterPanel from "primevue/splitterpanel";

import SchemeEditor from "@/arches_lingo/components/scheme/editor/SchemeEditor.vue";
import SchemeLabel from "@/arches_lingo/components/scheme/SchemeLabel/SchemeLabel.vue";
import SchemeNamespace from "@/arches_lingo/components/scheme/SchemeNamespace/SchemeNamespace.vue";
import SchemeNote from "@/arches_lingo/components/scheme/SchemeNote/SchemeNote.vue";
import SchemeStandard from "@/arches_lingo/components/scheme/SchemeStandard/SchemeStandard.vue";
import SchemeLicense from "@/arches_lingo/components/scheme/SchemeLicense/SchemeLicense.vue";

import {
    CLOSED,
    EDIT,
    MAXIMIZED,
    MINIMIZED,
    NEW,
    VIEW,
} from "@/arches_lingo/constants.ts";

const route = useRoute();
const { $gettext } = useGettext();

const editorPanelKey = ref(0);
const editorTileId = ref();
const editorState = ref(CLOSED);
const selectedComponentDatum = ref();

const resourceInstanceId = computed<string | undefined>(() => {
    if (route.params.id !== NEW) {
        return route.params.id as string;
    }

    return undefined;
});

const componentData = ref([
    {
        component: markRaw(SchemeLabel),
        componentName: "SchemeLabel",
        sectionTitle: $gettext("Scheme Label"),
        graphSlug: "scheme",
        nodegroupAlias: "appellative_status",
        key: 0,
    },
    {
        component: markRaw(SchemeNamespace),
        componentName: "SchemeNamespace",
        sectionTitle: $gettext("Scheme Namespace"),
        graphSlug: "scheme",
        nodegroupAlias: "namespace",
        key: 0,
    },
    {
        component: markRaw(SchemeNote),
        componentName: "SchemeNote",
        sectionTitle: $gettext("Scheme Note"),
        graphSlug: "scheme",
        nodegroupAlias: "statement",
        key: 0,
    },
    {
        component: markRaw(SchemeStandard),
        componentName: "SchemeStandard",
        sectionTitle: $gettext("Scheme Standard"),
        graphSlug: "scheme",
        nodegroupAlias: "creation",
        key: 0,
    },
    {
        component: markRaw(SchemeLicense),
        componentName: "SchemeLicense",
        sectionTitle: $gettext("Scheme Rights"),
        graphSlug: "scheme",
        nodegroupAlias: "rights",
        key: 0,
    },
]);

function closeEditor() {
    selectedComponentDatum.value = null;
    editorState.value = CLOSED;
    editorTileId.value = null;
    editorPanelKey.value += 1;
}

function openEditor(componentName: string, tileId?: string) {
    selectedComponentDatum.value = componentData.value.find(
        (componentDatum) => {
            return componentDatum.componentName === componentName;
        },
    );

    editorTileId.value = tileId;
    editorState.value = MINIMIZED;
    editorPanelKey.value += 1;
}

function maximizeEditor() {
    editorState.value = MAXIMIZED;
}

function minimizeEditor() {
    editorState.value = MINIMIZED;
}

function refreshReportSection(componentName: string) {
    const componentDatum = componentData.value.find((componentDatum) => {
        return componentDatum.componentName === componentName;
    });

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
                v-for="componentDatum in componentData"
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
            :key="editorPanelKey"
            :size="editorState === MINIMIZED ? 33 : 100"
        >
            <SchemeEditor
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
            </SchemeEditor>
        </SplitterPanel>
    </Splitter>
</template>
