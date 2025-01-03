<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";
import Button from "primevue/button";
import SchemeReportSection from "@/arches_lingo/components/scheme/report/SchemeSection.vue";
import NonLocalizedString from "@/arches_lingo/components/generic/NonLocalizedString.vue";
import {
    createScheme,
    fetchSchemeNamespace,
    updateSchemeNamespace,
} from "@/arches_lingo/api.ts";
import {
    EDIT,
    ERROR,
    NEW,
    OPEN_EDITOR,
    UPDATED,
    VIEW,
} from "@/arches_lingo/constants.ts";
import { useToast } from "primevue/usetoast";

import type {
    DataComponentMode,
    SchemeNamespaceUpdate,
    SchemeInstance,
} from "@/arches_lingo/types";

const toast = useToast();
const { $gettext } = useGettext();
const schemeInstance = ref<SchemeInstance>({});
const route = useRoute();
const router = useRouter();

defineProps<{
    mode?: DataComponentMode;
}>();

const emit = defineEmits([OPEN_EDITOR, UPDATED]);

defineExpose({ getSectionValue });

onMounted(async () => {
    getSectionValue();
});

async function save() {
    try {
        let updated;
        if (route.params.id === NEW) {
            updated = await createScheme(schemeInstance.value);
            await router.push({
                name: "scheme",
                params: { id: updated.resourceinstanceid },
            });
        } else {
            updated = await updateSchemeNamespace(
                route.params.id as string,
                schemeInstance.value,
            );
        }
        schemeInstance.value = updated;
        emit(UPDATED);
    } catch (error) {
        toast.add({
            severity: ERROR,
            summary: $gettext("Error saving scheme"),
            detail: (error as Error).message,
        });
    }
}

async function getSectionValue() {
    if (route.params.id === NEW) {
        return;
    }
    try {
        const response = await fetchSchemeNamespace(route.params.id as string);
        schemeInstance.value = response;
    } catch (error) {
        toast.add({
            severity: ERROR,
            summary: $gettext("Error"),
            detail:
                error instanceof Error
                    ? error.message
                    : $gettext(
                          "Could not fetch the namespace for the resource",
                      ),
        });
    }
}

function onNamespaceNameUpdate(val: string) {
    const namespaceValue = schemeInstance.value as SchemeNamespaceUpdate;
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
                @open-editor="emit(OPEN_EDITOR)"
            >
                <NonLocalizedString
                    :value="schemeInstance?.namespace?.namespace_name"
                    :mode="VIEW"
                />
                <!-- Discussion of namespace_type indicated it should not be displayed or edited manually,
                 if this changes, the ControlledListItem widget can be used.-->
            </SchemeReportSection>
        </div>
        <div v-if="mode === EDIT">
            <NonLocalizedString
                :value="schemeInstance?.namespace?.namespace_name ?? ''"
                :mode="EDIT"
                @update="onNamespaceNameUpdate"
            />
            <Button
                :label="$gettext('Update')"
                @click="save"
            />
        </div>
    </div>
</template>
