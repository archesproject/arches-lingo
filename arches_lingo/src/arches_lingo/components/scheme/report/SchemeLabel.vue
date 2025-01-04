<script setup lang="ts">
import { useGettext } from "vue3-gettext";
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { useToast } from "primevue/usetoast";

import {
    EDIT,
    ERROR,
    OPEN_EDITOR,
    NEW,
    VIEW,
    UPDATED,
} from "@/arches_lingo/constants.ts";
import { deleteSchemeLabelTile, fetchSchemeLabel } from "@/arches_lingo/api.ts";
import LabelEditor from "@/arches_lingo/components/generic/LabelEditor.vue";
import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import ResourceInstanceRelationships from "@/arches_lingo/components/generic/ResourceInstanceRelationships.vue";
import ReferenceDatatype from "@/arches_lingo/components/generic/ReferenceDatatype.vue";
import SchemeReportSection from "@/arches_lingo/components/scheme/report/SchemeSection.vue";

import type {
    AppellativeStatus,
    DataComponentMode,
    MetaStringText,
    SchemeInstance,
} from "@/arches_lingo/types.ts";
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
        args?: Array<object>;
    }>(),
    {
        mode: VIEW,
        tileId: null, // editor arg specifying what tile to operate on.
    },
);
const schemeInstance = ref<SchemeInstance>();

defineExpose({ getSectionValue });

const emit = defineEmits([OPEN_EDITOR, UPDATED]);

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
        emit(OPEN_EDITOR, appellativeStatus.tileid);
    } else {
        toast.add({
            severity: ERROR,
            summary: $gettext("Error"),
            detail: $gettext("Could not find the selected label to edit"),
        });
    }
}

function update() {
    emit(UPDATED);
}
</script>

<template>
    <div v-if="mode === VIEW">
        <SchemeReportSection
            :title-text="$gettext('Scheme Labels')"
            @open-editor="emit(OPEN_EDITOR)"
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
                    <ReferenceDatatype
                        :value="
                            (rowData as AppellativeStatus)
                                .appellative_status_ascribed_relation
                        "
                    >
                    </ReferenceDatatype>
                </template>
                <template #language="{ rowData }">
                    <ReferenceDatatype
                        :value="
                            (rowData as AppellativeStatus)
                                .appellative_status_ascribed_name_language
                        "
                    >
                    </ReferenceDatatype>
                </template>
                <template #drawer="{ rowData }">
                    <div>
                        <span>{{ $gettext("Bibliographic Sources:") }}</span>
                        <ResourceInstanceRelationships
                            :value="
                                (rowData as AppellativeStatus)
                                    .appellative_status_data_assignment_object_used
                            "
                        ></ResourceInstanceRelationships>
                    </div>
                    <div>
                        <span>{{ $gettext("Contributors:") }}</span>
                        <ResourceInstanceRelationships
                            :value="
                                (rowData as AppellativeStatus)
                                    .appellative_status_data_assignment_actor
                            "
                        ></ResourceInstanceRelationships>
                    </div>
                </template>
            </MetaStringViewer>
        </SchemeReportSection>
    </div>
    <div v-if="mode === EDIT">
        <div
            v-for="appellative_status in schemeInstance?.appellative_status"
            :key="appellative_status.tileid"
        >
            <LabelEditor
                :value="appellative_status"
                @update="update"
            ></LabelEditor>
        </div>
    </div>
</template>
<style scoped>
:deep(.drawer) {
    padding: 1rem 2rem;
}
</style>
