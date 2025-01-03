<script setup lang="ts">
import { useGettext } from "vue3-gettext";
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import {
    EDIT,
    ERROR,
    OPEN_EDITOR,
    NEW,
    VIEW,
} from "@/arches_lingo/constants.ts";
import type {
    AppellativeStatus,
    DataComponentMode,
    MetaStringText,
    SchemeInstance,
} from "@/arches_lingo/types.ts";
import { deleteSchemeLabelTile, fetchSchemeLabel } from "@/arches_lingo/api.ts";
import SchemeReportSection from "@/arches_lingo/components/scheme/report/SchemeSection.vue";
import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import ResourceInstanceRelationships from "@/arches_lingo/components/generic/ResourceInstanceRelationships.vue";
import ControlledListItem from "@/arches_lingo/components/generic/ControlledListItem.vue";
import { useToast } from "primevue/usetoast";

const schemeInstance = ref<SchemeInstance>({});
const { $gettext } = useGettext();
const toast = useToast();
const route = useRoute();
const metaStringLabel: MetaStringText = {
    deleteConfirm: $gettext("Are you sure you want to delete this label?"),
    language: $gettext("Label Language"),
    name: $gettext("Label Name"),
    type: $gettext("Label Type"),
    noRecords: $gettext("No scheme labels were found."),
};

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

defineExpose({ getSectionValue });

const emits = defineEmits([OPEN_EDITOR]);

onMounted(() => {
    getSectionValue();
});

async function getSectionValue() {
    if (route.params.id === NEW) {
        return;
    }
    try {
        const result = await fetchSchemeLabel(route.params.id as string);
        schemeInstance.value = {
            appellative_status: result.appellative_status,
        };
    } catch (error) {
        toast.add({
            severity: ERROR,
            summary: $gettext("Error"),
            detail:
                error instanceof Error
                    ? error.message
                    : $gettext("Could not fetch the labels for the resource"),
        });
    }
}

async function deleteSectionValue(tileId: string) {
    let result = false;
    try {
        result = await deleteSchemeLabelTile(route.params.id as string, tileId);
    } catch (error) {
        toast.add({
            severity: ERROR,
            summary: $gettext("Error"),
            detail:
                error instanceof Error
                    ? error.message
                    : $gettext("Could not delete selected label"),
        });
    }

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
            severity: ERROR,
            summary: $gettext("Error"),
            detail: $gettext("Could not find the selected label to edit"),
        });
    }
}

// async function save() {
//     // todo for Johnathan.  This function will save the values of the form back to arches.
// }

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
            <MetaStringViewer
                :meta-strings="schemeInstance?.appellative_status"
                :meta-string-text="metaStringLabel"
                @edit-string="editSectionValue"
                @delete-string="deleteSectionValue"
            >
                <template #name="{ rowData }">
                    <span>
                        {{
                            (rowData as AppellativeStatus)
                                .appellative_status_ascribed_name_content
                        }}
                    </span>
                </template>
                <template #type="{ rowData }">
                    <ControlledListItem
                        :value="
                            (rowData as AppellativeStatus)
                                .appellative_status_ascribed_relation
                        "
                    />
                </template>
                <template #language="{ rowData }">
                    <ControlledListItem
                        :value="
                            (rowData as AppellativeStatus)
                                .appellative_status_ascribed_name_language
                        "
                    />
                </template>
                <template #drawer="{ rowData }">
                    <div>
                        <span>{{ $gettext("Bibliographic Sources:") }}</span>
                        <ResourceInstanceRelationships
                            :value="
                                (rowData as AppellativeStatus)
                                    .appellative_status_data_assignment_object_used
                            "
                        />
                    </div>
                    <div>
                        <span>{{ $gettext("Contributors:") }}</span>
                        <ResourceInstanceRelationships
                            :value="
                                (rowData as AppellativeStatus)
                                    .appellative_status_data_assignment_actor
                            "
                        />
                    </div>
                </template>
            </MetaStringViewer>
        </SchemeReportSection>
    </div>
    <div v-if="mode === EDIT"><!-- todo for Johnathan-->abc</div>
</template>
<style scoped>
:deep(.drawer) {
    padding: 1rem 2rem;
}
</style>
