<script setup lang="ts">
import { useGettext } from "vue3-gettext";
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import { VIEW, EDIT, OPEN_EDITOR } from "@/arches_lingo/constants.ts";
import type {
    DataComponentMode,
    SchemeInstance,
} from "@/arches_lingo/types.ts";
import { deleteSchemeLabelTile, fetchSchemeLabel } from "@/arches_lingo/api.ts";
import SchemeReportSection from "@/arches_lingo/components/scheme/report/SchemeSection.vue";
import LabelViewer from "@/arches_lingo/components/generic/LabelViewer.vue";
import { useToast } from "primevue/usetoast";

const schemeInstance = ref<SchemeInstance>();
const { $gettext } = useGettext();
const toast = useToast();
const route = useRoute();

withDefaults(
    defineProps<{
        mode?: DataComponentMode;
        tileId?: string | null;
    }>(),
    {
        mode: VIEW,
        tileId: null, // editor arg specifying what tile to operate on.
    },
);

defineExpose({ save, getSectionValue });

const emits = defineEmits([OPEN_EDITOR]);

onMounted(() => {
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

function editSectionValue(tileId: string) {
    const appellativeStatus = schemeInstance.value?.appellative_status?.find(
        (tile) => tile.tileid === tileId,
    );
    if (appellativeStatus && appellativeStatus.tileid === tileId) {
        emits(OPEN_EDITOR, appellativeStatus.tileid);
    } else {
        toast.add({
            summary: $gettext("Error"),
            detail: $gettext("Could not find the selected label to edit."),
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
    <div v-if="mode === VIEW">
        <SchemeReportSection
            :title-text="$gettext('Scheme Labels')"
            @open-editor="emits(OPEN_EDITOR)"
        >
            <LabelViewer
                :value="schemeInstance?.appellative_status"
                @edit-label="editSectionValue"
                @delete-label="deleteSectionValue"
            ></LabelViewer>
        </SchemeReportSection>
    </div>
    <div v-if="mode === EDIT"><!-- todo for Johnathan-->abc</div>
</template>
<style scoped>
:deep(.drawer) {
    padding: 1rem 2rem;
}
</style>
