<script setup lang="ts">
import { useGettext } from "vue3-gettext";

import ComponentManager from "@/arches_lingo/components/generic/ComponentManager/ComponentManager.vue";

import ConceptHeader from "@/arches_lingo/components/concept/ConceptHeader.vue";
import ConceptLabel from "@/arches_lingo/components/concept/ConceptLabel/ConceptLabel.vue";
import ConceptNote from "@/arches_lingo/components/concept/ConceptNote/ConceptNote.vue";
import ConceptRelationship from "@/arches_lingo/components/concept/ConceptRelationship/ConceptRelationship.vue";
import ConceptMatch from "@/arches_lingo/components/concept/ConceptMatch/ConceptMatch.vue";
import HierarchicalPosition from "@/arches_lingo/components/concept/HierarchicalPosition/HierarchicalPosition.vue";
import ConceptImages from "@/arches_lingo/components/concept/ConceptImages/ConceptImages.vue";

const { $gettext } = useGettext();

const componentData = [
    {
        component: ConceptHeader,
        componentName: "ConceptHeader",
        sectionTitle: $gettext("Concept Metadata"),
        graphSlug: "concept",
        nodegroupAlias: "",
    },
    {
        component: ConceptLabel,
        componentName: "ConceptLabel",
        sectionTitle: $gettext("Concept Labels"),
        graphSlug: "concept",
        nodegroupAlias: "appellative_status",
    },
    {
        component: ConceptNote,
        componentName: "ConceptNote",
        sectionTitle: $gettext("Concept Notes"),
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
    {
        component: ConceptRelationship,
        componentName: "ConceptRelationship",
        sectionTitle: $gettext("Associated Concepts"),
        graphSlug: "concept",
        nodegroupAlias: "relation_status",
    },
    {
        component: ConceptMatch,
        componentName: "ConceptMatch",
        sectionTitle: $gettext("Matched Concepts"),
        graphSlug: "concept",
        nodegroupAlias: "match_status",
    },
    {
        component: HierarchicalPosition,
        componentName: "HierarchicalPosition",
        sectionTitle: $gettext("Hierarchical Position"),
        graphSlug: "concept",
        nodegroupAlias: "classification_status",
    },
];
</script>

<template>
    <ComponentManager :component-data="componentData" />
</template>
