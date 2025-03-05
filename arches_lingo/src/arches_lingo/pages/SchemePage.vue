<script setup lang="ts">
import { useGettext } from "vue3-gettext";

import ComponentManager from "@/arches_lingo/components/generic/ComponentManager/ComponentManager.vue";

import SchemeLabel from "@/arches_lingo/components/scheme/SchemeLabel/SchemeLabel.vue";
import SchemeNamespace from "@/arches_lingo/components/scheme/SchemeNamespace/SchemeNamespace.vue";
import SchemeNote from "@/arches_lingo/components/scheme/SchemeNote/SchemeNote.vue";
import SchemeStandard from "@/arches_lingo/components/scheme/SchemeStandard/SchemeStandard.vue";
import SchemeLicense from "@/arches_lingo/components/scheme/SchemeLicense/SchemeLicense.vue";

const { $gettext } = useGettext();

const componentData = [
    {
        component: SchemeLabel,
        componentName: "SchemeLabel",
        sectionTitle: $gettext("Scheme Label"),
        graphSlug: "scheme",
        nodegroupAlias: "appellative_status",
    },
    {
        component: SchemeNamespace,
        componentName: "SchemeNamespace",
        sectionTitle: $gettext("Scheme Namespace"),
        graphSlug: "scheme",
        nodegroupAlias: "namespace",
    },
    {
        component: SchemeNote,
        componentName: "SchemeNote",
        sectionTitle: $gettext("Scheme Note"),
        graphSlug: "scheme",
        nodegroupAlias: "statement",
    },
    {
        component: SchemeStandard,
        componentName: "SchemeStandard",
        sectionTitle: $gettext("Scheme Standard"),
        graphSlug: "scheme",
        nodegroupAlias: "creation",
    },
    {
        component: SchemeLicense,
        componentName: "SchemeLicense",
        sectionTitle: $gettext("Scheme Rights"),
        graphSlug: "scheme",
        nodegroupAlias: "rights",
    },
];
</script>

<template>
    <ComponentManager :component-data="componentData" />
</template>
