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

        <NonLocalizedStringWidget
            v-if="props.tileData"
            node-alias="namespace_name"
            :graph-slug="props.graphSlug"
            :initial-value="props.tileData.aliased_data.namespace_name"
            :mode="VIEW"
        />
        <div v-else>
            <p class="section-message">
                {{ $gettext("No Scheme Namespaces were found.") }}
            </p>
        </div>
    </div>
</template>

<style scoped>
.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--p-form-field-border-color);
    padding-bottom: 0.5rem;
}

h2 {
    margin: 0;
    font-size: 1.2rem;
    font-weight: 400;
    color: var(--p-neutral-500);
}

.add-button {
    height: 2rem;
    font-size: 0.9rem;
    font-weight: 400;
    min-width: 10rem;
    border-radius: 2px;
}

.section-message {
    padding: 0.5rem 0;
    color: var(--p-inputtext-placeholder-color);
}
</style>
