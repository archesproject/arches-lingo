<script setup lang="ts">
import { ref } from "vue";
import Splitter from "primevue/splitter";
import SplitterPanel from "primevue/splitterpanel";
import SchemeLicense from "@/arches_lingo/components/scheme/report/SchemeLicense.vue";
import SchemeNote from "@/arches_lingo/components/scheme/report/SchemeNote.vue";
import SchemeNamespace from "@/arches_lingo/components/scheme/report/SchemeNamespace.vue";
import SchemeStandard from "@/arches_lingo/components/scheme/report/SchemeStandard.vue";
import SchemeAuthority from "@/arches_lingo/components/scheme/report/SchemeAuthority.vue";
import SchemeEditor from "@/arches_lingo/components/scheme/editor/SchemeEditor.vue";

const editorVisible = ref(false);
const sectionVisible = ref(true);
const editorTab = ref<string>();
type sectionTypes =
    | typeof SchemeNamespace
    | typeof SchemeLicense
    | typeof SchemeStandard
    | typeof SchemeAuthority
    | typeof SchemeNote;
const childRefs = ref<Array<sectionTypes>>([]);
const onMaximize = () => {
    editorVisible.value = true;
    sectionVisible.value = false;
};

const onSide = () => {
    editorVisible.value = true;
    editorVisible.value = true;
    sectionVisible.value = true;
};

const onClose = () => {
    editorVisible.value = false;
    sectionVisible.value = true;
};

const onOpenEditor = (tab: string) => {
    editorTab.value = tab;
    editorVisible.value = true;
    sectionVisible.value = true;
};
const onUpdated = () => {
    childRefs.value.forEach((ref) => {
        ref?.getSectionValue();
    });
};

const components = [
    { component: SchemeNote, id: "note", props: {} },
    { component: SchemeAuthority, id: "authority", props: {} },
    { component: SchemeStandard, id: "standard", props: {} },
    { component: SchemeLicense, id: "license", props: {} },
    { component: SchemeNamespace, id: "namespace", props: {} },
];

const getRef = (el: object | null, index: number) => {
    if (el != null) childRefs.value[index] = el as sectionTypes;
};
</script>

<template>
    <Splitter style="height: 100%">
        <SplitterPanel
            v-if="sectionVisible"
            :size="66"
            :min-size="33"
        >
            <template
                v-for="(component, index) in components"
                :key="component.id"
            >
                <component
                    :is="component.component"
                    :ref="(el) => getRef(el, index)"
                    v-bind="component.props"
                    @open-editor="onOpenEditor(component.id)"
                />
            </template>
        </SplitterPanel>
        <SplitterPanel
            v-if="editorVisible"
            :size="33"
            :min-size="33"
        >
            <SchemeEditor
                v-if="editorTab"
                :editor-max="sectionVisible"
                :active-tab="editorTab"
                @maximize="onMaximize"
                @side="onSide"
                @close="onClose"
                @updated="onUpdated"
            />
        </SplitterPanel>
    </Splitter>
</template>
