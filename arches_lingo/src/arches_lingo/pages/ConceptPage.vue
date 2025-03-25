<script setup lang="ts">
import { useGettext } from "vue3-gettext";

import ComponentManager from "@/arches_lingo/components/generic/ComponentManager/ComponentManager.vue";

import ConceptLabel from "@/arches_lingo/components/concept/ConceptLabel/ConceptLabel.vue";
import ConceptNote from "@/arches_lingo/components/concept/ConceptNote/ConceptNote.vue";
import ConceptImages from "@/arches_lingo/components/concept/ConceptImages/ConceptImages.vue";

const { $gettext } = useGettext();

const componentData = [
    {
        component: ConceptLabel,
        componentName: "ConceptLabel",
        sectionTitle: $gettext("Concept Label"),
        graphSlug: "concept",
        nodegroupAlias: "appellative_status",
    },
    {
        component: ConceptNote,
        componentName: "ConceptNote",
        sectionTitle: $gettext("Concept Note"),
        graphSlug: "concept",
        nodegroupAlias: "statement",
    },
    {
        component: ConceptImages,
        componentName: "ConceptImages",
        sectionTitle: $gettext("Concept Images"),
        graphSlug: "concept",
        nodegroupAlias: "depicting_digital_asset_internal",
    },
];
</script>

<template>
    <ComponentManager :component-data="componentData" />
</template>
