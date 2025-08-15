<script setup lang="ts">
import { computed, inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

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
        return $gettext("Edit Namespace");
    } else {
        return $gettext("Add Namespace");
    }
});
</script>

<template>
    <div class="viewer-section">
        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>

            <Button
                :label="buttonLabel"
                class="add-button"
                @click="
                    openEditor!(props.componentName, props.tileData?.tileid)
                "
            ></Button>
        </div>

        <GenericWidget
            v-if="props.tileData"
            node-alias="namespace_name"
            :graph-slug="props.graphSlug"
            :value="props.tileData.aliased_data.namespace_name"
            :mode="VIEW"
        />
        <div
            v-else
            class="section-message"
        >
            {{ $gettext("No Scheme Namespaces were found.") }}
        </div>
    </div>
</template>
