<script setup lang="ts">
import { computed, inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";

import type { SchemeCreation } from "@/arches_lingo/types.ts";

const props = defineProps<{
    tileData: SchemeCreation | undefined;
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
        return $gettext("Edit Scheme Standard");
    } else {
        return $gettext("Add New Scheme Standard");
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

    <ResourceInstanceMultiSelectWidget
        v-if="props.tileData"
        node-alias="creation_sources"
        :graph-slug="props.graphSlug"
        :initial-value="props.tileData.creation_sources"
        :mode="VIEW"
    />

    <div v-else>
        <p>{{ $gettext("No Scheme Standards were found.") }}</p>
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
