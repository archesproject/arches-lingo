<script setup lang="ts">
import { computed, inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import NonLocalizedStringWidget from "@/arches_component_lab/widgets/NonLocalizedStringWidget/NonLocalizedStringWidget.vue";
import ReferenceSelectWidget from "@/arches_controlled_lists/widgets/ReferenceSelectWidget/ReferenceSelectWidget.vue";
import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";

import type { SchemeRights } from "@/arches_lingo/types";

const props = defineProps<{
    tileData: SchemeRights | undefined;
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
        return $gettext("Edit Scheme Rights");
    } else {
        return $gettext("Add New Scheme Rights");
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

    <div v-if="props.tileData">
        <ResourceInstanceMultiSelectWidget
            node-alias="right_holder"
            :graph-slug="props.graphSlug"
            :initial-value="props.tileData?.right_holder"
            :mode="VIEW"
        />
        <ReferenceSelectWidget
            node-alias="right_type"
            :graph-slug="props.graphSlug"
            :initial-value="props.tileData?.right_type"
            :mode="VIEW"
        />
        <NonLocalizedStringWidget
            node-alias="right_statement_content"
            :graph-slug="props.graphSlug"
            :initial-value="
                props.tileData?.right_statement?.right_statement_content
            "
            :mode="VIEW"
        />
        <ReferenceSelectWidget
            node-alias="right_statement_language"
            :graph-slug="props.graphSlug"
            :initial-value="
                props.tileData?.right_statement?.right_statement_language
            "
            :mode="VIEW"
        />
        <ReferenceSelectWidget
            node-alias="right_statement_type"
            :graph-slug="props.graphSlug"
            :initial-value="
                props.tileData?.right_statement?.right_statement_type
            "
            :mode="VIEW"
        />
        <ReferenceSelectWidget
            node-alias="right_statement_type_metatype"
            :graph-slug="props.graphSlug"
            :initial-value="
                props.tileData?.right_statement?.right_statement_type_metatype
            "
            :mode="VIEW"
        />
    </div>
    <div v-else>
        <p>{{ $gettext("No Scheme Rights were found.") }}</p>
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
