<script setup lang="ts">
import { onBeforeUpdate, onUpdated, ref } from "vue";
import { useGettext } from "vue3-gettext";
import Button from "primevue/button";

import Tabs from "primevue/tabs";
import TabList from "primevue/tablist";
import Tab from "primevue/tab";
import TabPanels from "primevue/tabpanels";
import TabPanel from "primevue/tabpanel";
import SchemeNamespace from "@/arches_lingo/components/scheme/report/SchemeNamespace.vue";
import SchemeStandard from "@/arches_lingo/components/scheme/report/SchemeStandard.vue";
import SchemeLabel from "@/arches_lingo/components/scheme/report/SchemeLabel.vue";
type sectionTypes = typeof SchemeNamespace;

const { $gettext } = useGettext();
const EDIT = "edit";
const props = defineProps<{
    editorMax: boolean;
    activeTab: string;
    tileId?: string;
}>();
const childRefs = ref<Array<sectionTypes>>([]);
const schemeComponents = [
    {
        component: SchemeLabel,
        id: "label",
        editorTabName: $gettext("Scheme Label"),
    },
    {
        component: SchemeNamespace,
        id: "namespace",
        editorTabName: $gettext("Scheme Namespace"),
    },
    {
        component: SchemeStandard,
        id: "standard",
        editorTabName: $gettext("Scheme Standards Followed"),
    },
];

const emit = defineEmits(["maximize", "side", "close", "updated"]);

onBeforeUpdate(() => {
    childRefs.value = [];
});

function toggleSize() {
    if (props.editorMax) {
        emit("maximize");
    } else {
        emit("side");
    }
}

function getRef(el: object | null, index: number) {
    if (el != null) childRefs.value[index] = el as sectionTypes;
}

async function updateScheme() {
    await Promise.all(
        childRefs.value.map(async (ref) => {
            return ref.save();
        }),
    );

    emit("updated");
}
</script>

<template>
    <div class="header">
        <div>
            <h3>{{ $gettext("Editor Tools") }}</h3>
            <div>
                <Button
                    :aria-label="$gettext('toggle editor size')"
                    @click="toggleSize"
                >
                    <i
                        :class="{
                            pi: true,
                            'pi-window-maximize': props.editorMax,
                            'pi-window-minimize': !props.editorMax,
                        }"
                        aria-hidden="true"
                    />
                </Button>
                <Button
                    :aria-label="$gettext('close editor')"
                    @click="$emit('close')"
                >
                    <i
                        class="pi pi-times"
                        aria-hidden="true"
                    />
                </Button>
            </div>
        </div>
    </div>
    <div class="content">
        <Tabs :value="activeTab">
            <TabList>
                <template
                    v-for="component in schemeComponents"
                    :key="component.id"
                >
                    <Tab :value="component.id">{{
                        component.editorTabName
                    }}</Tab>
                </template>
            </TabList>
            <TabPanels>
                <template
                    v-for="(component, index) in schemeComponents"
                    :key="component.id"
                >
                    <TabPanel :value="component.id">
                        <component
                            :is="component.component"
                            v-bind="{ mode: EDIT, tileId: props.tileId }"
                            :ref="(el) => getRef(el, index)"
                            v-on="{ updated: onUpdated }"
                        />
                    </TabPanel>
                </template>
            </TabPanels>
        </Tabs>
        <Button
            :label="$gettext('Update')"
            @click="updateScheme"
        ></Button>
    </div>
</template>
<style scoped>
.header div {
    margin: 0 1rem;
    display: flex;
    align-items: center;
}
.header div h3 {
    flex: 1;
}
</style>
