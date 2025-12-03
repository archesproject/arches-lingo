<script setup lang="ts">
import { useGettext } from "vue3-gettext";

import ComponentManager from "@/arches_lingo/components/generic/ComponentManager/ComponentManager.vue";

import SchemeHeader from "@/arches_lingo/components/scheme/SchemeHeader/SchemeHeader.vue";
import SchemeLabel from "@/arches_lingo/components/scheme/SchemeLabel/SchemeLabel.vue";
import SchemeNamespace from "@/arches_lingo/components/scheme/SchemeNamespace/SchemeNamespace.vue";
import SchemeNote from "@/arches_lingo/components/scheme/SchemeNote/SchemeNote.vue";
import SchemeStandard from "@/arches_lingo/components/scheme/SchemeStandard/SchemeStandard.vue";
import SchemeLicense from "@/arches_lingo/components/scheme/SchemeLicense/SchemeLicense.vue";

const { $gettext } = useGettext();

const componentData = [
    {
        component: SchemeHeader,
        componentName: "SchemeHeader",
        sectionTitle: $gettext("Scheme Metadata"),
        graphSlug: "scheme",
        nodegroupAlias: "",
    },
    {
        component: SchemeLabel,
        componentName: "SchemeLabel",
        sectionTitle: $gettext("Scheme Labels"),
        graphSlug: "scheme",
        nodegroupAlias: "appellative_status",
    },
    {
        component: SchemeNote,
        componentName: "SchemeNote",
        sectionTitle: $gettext("Scheme Notes"),
        graphSlug: "scheme",
        nodegroupAlias: "statement",
    },
    {
        component: SchemeNamespace,
        componentName: "SchemeNamespace",
        sectionTitle: $gettext("Scheme Namespace"),
        graphSlug: "scheme",
        nodegroupAlias: "namespace",
    },
    {
        component: SchemeStandard,
        componentName: "SchemeStandard",
        sectionTitle: $gettext("Scheme Standards"),
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
