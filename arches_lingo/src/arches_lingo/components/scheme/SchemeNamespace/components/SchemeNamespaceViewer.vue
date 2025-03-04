<script setup lang="ts">
import { computed, inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import NonLocalizedStringWidget from "@/arches_component_lab/widgets/NonLocalizedStringWidget/NonLocalizedStringWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";

import type { SchemeNamespace } from "@/arches_lingo/types.ts";

const props = defineProps<{
    tileData: SchemeNamespace | undefined;
    graphSlug: string;
    componentName: string;
    sectionTitle: string;
}>();

const { $gettext } = useGettext();

const openEditor =
    inject<(componentName: string, tileId: string | undefined) => void>(
        "openEditor",
    );

const buttonLabel = computed(() => {
    if (props.tileData) {
        return $gettext("Edit Scheme Namespace");
    } else {
        return $gettext("Add New Scheme Namespace");
    }
});
</script>

<template>
    <div class="section-header">
        <h2>{{ props.sectionTitle }}</h2>

        <Button
            :label="buttonLabel"
            @click="openEditor!(props.componentName, props.tileData?.tileid)"
        ></Button>
    </div>

    <NonLocalizedStringWidget
        v-if="props.tileData"
        node-alias="namespace_name"
        :graph-slug="props.graphSlug"
        :initial-value="props.tileData.namespace_name"
        :mode="VIEW"
    />
    <div v-else>
        <p>{{ $gettext("No Scheme Namespaces were found.") }}</p>
    </div>
</template>

<style scoped>
.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 0.125rem solid var(--p-menubar-border-color);
}
</style>
