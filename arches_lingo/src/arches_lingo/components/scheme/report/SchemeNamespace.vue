<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { useGettext } from "vue3-gettext";

import SchemeReportSection from "@/arches_lingo/components/scheme/report/SchemeSection.vue";
import NonLocalizedString from "@/arches_lingo/components/generic/NonLocalizedString.vue";
import {
    fetchSchemeNamespace,
    updateSchemeNamespace,
} from "@/arches_lingo/api.ts";
import type {
    DataComponentMode,
    SchemeNamespaceUpdate,
    SchemeInstance,
} from "@/arches_lingo/types";
import { VIEW, EDIT } from "@/arches_lingo/constants.ts";

const { $gettext } = useGettext();
const schemeNamespace = ref<SchemeInstance>();
const route = useRoute();

defineProps<{
    mode?: DataComponentMode;
}>();

defineEmits(["openEditor"]);

defineExpose({ save, getSectionValue });

onMounted(async () => {
    getSectionValue();
});

async function save() {
    await updateSchemeNamespace(
        route.params.id as string,
        schemeNamespace.value as SchemeInstance,
    );
}

async function getSectionValue() {
    const response = await fetchSchemeNamespace(route.params.id as string);
    schemeNamespace.value = response;
}

function onNamespaceNameUpdate(val: string) {
    const namespaceValue = schemeNamespace.value as SchemeNamespaceUpdate;
    if (!namespaceValue?.namespace) {
        namespaceValue.namespace = {
            namespace_name: val,
            namespace_type: [{ value: "namespace" }],
        };
    } else {
        namespaceValue.namespace.namespace_name = val;
        namespaceValue.namespace.namespace_type = [{ value: "namespace" }];
    }
}
</script>

<template>
    <div>
        <div v-if="!mode || mode === VIEW">
            <SchemeReportSection
                :title-text="$gettext('Scheme Namespace')"
                @open-editor="$emit('openEditor')"
            >
                <NonLocalizedString
                    :value="schemeNamespace?.namespace?.namespace_name"
                    :mode="VIEW"
                />
                <!-- Discussion of namespace_type indicated it should not be displayed or edited manually,
                 if this changes, the ControlledListItem widget can be used.-->
            </SchemeReportSection>
        </div>
        <div v-if="mode === EDIT">
            <NonLocalizedString
                :value="schemeNamespace?.namespace?.namespace_name ?? ''"
                :mode="EDIT"
                @update="onNamespaceNameUpdate"
            />
        </div>
    </div>
</template>
