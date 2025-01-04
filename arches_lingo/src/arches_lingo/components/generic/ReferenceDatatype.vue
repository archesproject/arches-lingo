<script setup lang="ts">
import { EDIT, VIEW } from "@/arches_lingo/constants.ts";
import ReferenceDatatypeViewer from "@/arches_lingo/components/generic/reference-datatype/ReferenceDatatypeViewer.vue";
import ReferenceDatatypeEditor from "@/arches_lingo/components/generic/reference-datatype/ReferenceDatatypeEditor.vue";

import type {
    ControlledListItem,
    DataComponentMode,
} from "@/arches_lingo/types";

defineProps<{
    mode?: DataComponentMode;
    value?: ControlledListItem[];
    multiValue?: boolean;
    options?: ControlledListItem[];
}>();
const emit = defineEmits(["update"]);
const onUpdate = (val: ControlledListItem[]) => {
    emit("update", val);
};
</script>
<template>
    <div>
        <div v-if="mode === VIEW">
            <ReferenceDatatypeViewer :value="value" />
        </div>
        <div v-if="mode === EDIT">
            <ReferenceDatatypeEditor
                :value="value"
                :options="options"
                :multi-value="multiValue"
                @update="onUpdate"
            />
        </div>
    </div>
</template>
