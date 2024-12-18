<script setup lang="ts">
import type {
    ControlledListItem,
    DataComponentMode,
} from "@/arches_lingo/types";
import ReferenceDatatypeViewer from "@/arches_lingo/components/generic/ReferenceDatatypeViewer.vue";
import ReferenceDatatypeEditor from "@/arches_lingo/components/generic/ReferenceDatatypeEditor.vue";
import ReferenceDatatypeListEditor from "@/arches_lingo/components/generic/ReferenceDatatypeListEditor.vue";
import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

const { mode = EDIT } = defineProps<{
    mode?: DataComponentMode;
    value?: ControlledListItem;
    multiValue?: string;
    options?: ControlledListItem[];
}>();
const emits = defineEmits(["update"]);
const onUpdate = (val: ControlledListItem) => {
    emits("update", val);
};
</script>
<template>
    <div>
        <div v-if="mode === VIEW">
            <ReferenceDatatypeViewer :value="value" />
        </div>
        <div v-if="mode === EDIT && multiValue === '1'">
            <ReferenceDatatypeEditor
                :value="value"
                @update="onUpdate"
            />
        </div>
        <div v-if="mode === EDIT && multiValue === 'n'">
            <ReferenceDatatypeListEditor
                :value="value"
                @update="onUpdate"
            />
        </div>
    </div>
</template>
