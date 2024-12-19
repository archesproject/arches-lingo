<script setup lang="ts">
import { useGettext } from "vue3-gettext";
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { useToast } from "primevue/usetoast";

import { VIEW, EDIT, OPEN_EDITOR } from "@/arches_lingo/constants.ts";
import { deleteSchemeLabelTile, fetchSchemeLabel } from "@/arches_lingo/api.ts";
import LabelViewer from "@/arches_lingo/components/generic/LabelViewer.vue";
import LabelEditor from "@/arches_lingo/components/generic/LabelEditor.vue";
import SchemeReportSection from "@/arches_lingo/components/scheme/report/SchemeSection.vue";

import type {
    DataComponentMode,
    SchemeInstance,
} from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();
const toast = useToast();
const route = useRoute();

withDefaults(
    defineProps<{
        mode?: DataComponentMode;
        args?: Array<object>;
        // todo for Johnathan - if obj empty, create new tile
        // if obj has values, load those values into the form
    }>(),
    {
        mode: VIEW,
        args: () => [],
    },
);
const schemeInstance = ref<SchemeInstance>();

defineExpose({ save, getSectionValue });

const emits = defineEmits([OPEN_EDITOR]);

onMounted(async () => {
    getSectionValue();
});

async function getSectionValue() {
    const result = await fetchSchemeLabel(route.params.id as string);
    schemeInstance.value = {
        appellative_status: result.appellative_status,
    };
}

async function deleteSectionValue(tileId: string) {
    const result = await deleteSchemeLabelTile(tileId);
    if (result) {
        getSectionValue();
    }
}

async function editSectionValue(tileId: string) {
    const appellativeStatus = schemeInstance.value?.appellative_status?.find(
        (tile) => {
            if (tile.tileid === tileId) {
                return true;
            } else {
                return false;
            }
        },
    );
    if (appellativeStatus && appellativeStatus.tileid === tileId) {
        emits(OPEN_EDITOR, appellativeStatus);
    } else {
        toast.add({
            severity: "error",
            summary: $gettext("Error"),
            detail: $gettext("Could not find the selected label to edit."),
            life: 3000,
        });
    }
}

async function save() {
    // todo for Johnathan.  This function will save the values of the form back to arches.
}

// async function update() {
//     // todo for Johnathan.  This function will handle the update emit when the user changes values in your form - you store those values in this section.
// }
</script>

<template>
    <div v-if="!mode || mode === VIEW">
        <SchemeReportSection
            :title-text="$gettext('Scheme Labels')"
            @open-editor="emits(OPEN_EDITOR)"
        >
            <LabelViewer
                :value="schemeInstance?.appellative_status"
                @edit-label="(tileId: string) => editSectionValue(tileId)"
                @delete-label="(tileId: string) => deleteSectionValue(tileId)"
            ></LabelViewer>
        </SchemeReportSection>
    </div>
    <div v-if="mode === EDIT">
        <div
            v-for="appellative_status in schemeInstance?.appellative_status"
            :key="appellative_status.tileid"
        >
            <LabelEditor :value="appellative_status"></LabelEditor>
        </div>
    </div>
</template>
<style scoped>
:deep(.drawer) {
    padding: 1rem 2rem;
}

:deep(.resource-instance-relationship-view) {
    padding: 0 0.25rem;
}
</style>
