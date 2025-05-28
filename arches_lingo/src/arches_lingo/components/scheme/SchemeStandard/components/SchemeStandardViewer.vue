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
        return $gettext("Add Standard");
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

        <ResourceInstanceMultiSelectWidget
            v-if="props.tileData"
            node-alias="creation_sources"
            :graph-slug="props.graphSlug"
            :initial-value="props.tileData.aliased_data.creation_sources"
            :mode="VIEW"
        />

        <div v-else>
            <p class="section-message">
                {{ $gettext("No Scheme Standards were found.") }}
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
    margin: 0;
}
</style>
