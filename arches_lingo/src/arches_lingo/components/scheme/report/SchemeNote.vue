<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useGettext } from "vue3-gettext";
import { useRoute } from "vue-router";
import { useToast } from "primevue/usetoast";
import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import SchemeReportSection from "@/arches_lingo/components/scheme/report/SchemeSection.vue";
import {
    deleteLingoTile,
    fetchLingoResourcePartial,
} from "@/arches_lingo/api.ts";
import {
    ERROR,
    NEW,
    OPEN_EDITOR,
    VIEW,
    EDIT,
    UPDATED,
} from "@/arches_lingo/constants.ts";
import NoteEditor from "@/arches_lingo/components/generic/NoteEditor.vue";
import type {
    DataComponentMode,
    MetaStringText,
    SchemeInstance,
    SchemeStatement,
} from "@/arches_lingo/types.ts";
import ResourceInstanceRelationships from "@/arches_lingo/components/generic/ResourceInstanceRelationships.vue";
import ReferenceDatatype from "@/arches_lingo/components/generic/ReferenceDatatype.vue";

const { $gettext } = useGettext();
const schemeInstance = ref<SchemeInstance>();
const route = useRoute();
const toast = useToast();
const metaStringLabel: MetaStringText = {
    deleteConfirm: $gettext("Are you sure you want to delete this note?"),
    language: $gettext("Note Language"),
    name: $gettext("Note Name"),
    type: $gettext("Note Type"),
    noRecords: $gettext("No scheme notes were found."),
};

const props = withDefaults(
    defineProps<{
        mode?: DataComponentMode;
        tileId?: string | null;
    }>(),
    {
        mode: VIEW,
        tileId: null, // editor arg specifying what tile to operate on.
    },
);

watch(props, () => {
    getSectionValue();
});

const emit = defineEmits([OPEN_EDITOR, UPDATED]);

defineExpose({ getSectionValue });

onMounted(() => {
    getSectionValue();
});

const selectedNote = computed(() => {
    return schemeInstance.value?.statement?.find(
        (tile) => tile.tileid === props.tileId,
    );
});

async function getSectionValue() {
    if (route.params.id === NEW) {
        return;
    }
    try {
        const result = await fetchLingoResourcePartial(
            "scheme",
            route.params.id as string,
            "statement",
        );
        schemeInstance.value = {
            statement: result.statement,
        };
    } catch (error) {
        toast.add({
            severity: ERROR,
            summary: $gettext("Error"),
            detail:
                error instanceof Error
                    ? error.message
                    : $gettext("Could not fetch the notes for the resource"),
        });
    }
}

async function deleteSectionValue(tileId: string) {
    let result = false;
    try {
        result = await deleteLingoTile("scheme", "statement", tileId);
    } catch (error) {
        toast.add({
            severity: ERROR,
            summary: $gettext("Error"),
            detail:
                error instanceof Error
                    ? error.message
                    : $gettext("Could not delete selected note"),
        });
    }

    if (result) {
        getSectionValue();
    }
}

function editSectionValue(tileId: string) {
    const schemeStatement = schemeInstance.value?.statement?.find(
        (tile) => tile.tileid === tileId,
    );
    if (schemeStatement && schemeStatement.tileid === tileId) {
        emit(OPEN_EDITOR, schemeStatement.tileid);
    } else {
        toast.add({
            severity: ERROR,
            summary: $gettext("Error"),
            detail: $gettext("Could not find the selected note to edit"),
        });
    }
}
async function update(tileId: string | undefined) {
    await emit(UPDATED);
    if (tileId) {
        await emit(OPEN_EDITOR, tileId);
    }
}
</script>

<template>
    <div v-if="mode === VIEW">
        <SchemeReportSection
            :title-text="$gettext('Scheme Notes')"
            :button-text="$gettext('Add New Scheme Note')"
            @open-editor="emit(OPEN_EDITOR)"
        >
            <MetaStringViewer
                :meta-strings="schemeInstance?.statement"
                :meta-string-text="metaStringLabel"
                @edit-string="editSectionValue"
                @delete-string="deleteSectionValue"
            >
                <template #name="{ rowData }">
                    <span>
                        {{ (rowData as SchemeStatement).statement_content_n1 }}
                    </span>
                </template>
                <template #type="{ rowData }">
                    <ReferenceDatatype
                        :value="(rowData as SchemeStatement).statement_type_n1"
                        :mode="VIEW"
                    />
                </template>
                <template #language="{ rowData }">
                    <ReferenceDatatype
                        :value="
                            (rowData as SchemeStatement).statement_language_n1
                        "
                        :mode="VIEW"
                    />
                </template>
                <template #drawer="{ rowData }">
                    <div>
                        <span>{{ $gettext("Bibliographic Sources:") }}</span>
                        <ResourceInstanceRelationships
                            :value="
                                (rowData as SchemeStatement)
                                    .statement_data_assignment_object_used
                            "
                        />
                    </div>
                    <div>
                        <span>{{ $gettext("Contributors:") }}</span>
                        <ResourceInstanceRelationships
                            :value="
                                (rowData as SchemeStatement)
                                    .statement_data_assignment_actor
                            "
                        />
                    </div>
                </template>
            </MetaStringViewer>
        </SchemeReportSection>
    </div>
    <div v-if="mode === EDIT">
        <NoteEditor
            :value="selectedNote"
            @update="update"
        />
    </div>
</template>
